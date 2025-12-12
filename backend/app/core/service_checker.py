import asyncio
import socket
import time as time_module
from typing import Optional, Tuple
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from ..models import Service, ServiceStatus
from .database import SessionLocal
from .notifications import emit_notification


async def check_http(target: str, timeout_sec: int) -> Tuple[bool, Optional[float]]:
    """
    Perform a simple HTTP GET check.
    Returns (is_up, latency_ms).
    """
    start = time_module.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            r = await client.get(target)
        latency = (time_module.perf_counter() - start) * 1000.0
        is_up = r.status_code < 500
        return is_up, latency
    except Exception:
        return False, None


async def check_tcp(target: str, timeout_sec: int) -> Tuple[bool, Optional[float]]:
    """
    Opens a TCP connection to host:port.
    target example: '192.168.1.10:25565'
    """
    if ":" not in target:
        return False, None
    host, port_str = target.split(":", 1)
    port = int(port_str)

    start = time_module.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout_sec,
        )
        writer.close()
        await writer.wait_closed()
        latency = (time_module.perf_counter() - start) * 1000.0
        return True, latency
    except Exception:
        return False, None


async def check_one_service(service: Service) -> Tuple[bool, Optional[float]]:
    if service.kind.upper() == "HTTP":
        return await check_http(service.target, service.timeout_sec)
    if service.kind.upper() == "TCP":
        return await check_tcp(service.target, service.timeout_sec)
    return False, None


async def service_checker_loop(interval_seconds: int = 30):
    """
    Background task that periodically checks all enabled services.
    """
    while True:
        db = SessionLocal()
        try:
            services = db.query(Service).filter(Service.enabled == True).all()

            now = datetime.utcnow()

            for s in services:
                status = s.status

                # Respect per-service check interval
                if status and status.last_checked_at:
                    elapsed = (now - status.last_checked_at).total_seconds()
                    if elapsed < s.check_interval_sec:
                        continue

                is_up, latency = await check_one_service(s)

                if status is None:
                    # create a new status row
                    status = ServiceStatus(
                        service_id=s.id,
                        is_up=is_up,
                        latency_ms=latency,
                        last_checked_at=now,
                        consecutive_failures=0 if is_up else 1,
                        last_change_at=now,
                    )
                    db.add(status)
                    previous_state = None
                else:
                    previous_state = status.is_up
                    status.is_up = is_up
                    status.latency_ms = latency
                    status.last_checked_at = now

                    if is_up:
                        # service recovered
                        if not previous_state:
                            status.last_change_at = now
                        status.consecutive_failures = 0
                    else:
                        # still failing
                        if previous_state:
                            status.last_change_at = now
                        status.consecutive_failures += 1

                db.commit()

                # Emit alerts when state flips, respecting alert flags
                if previous_state is not None and previous_state != status.is_up:
                    if (not status.is_up and s.alert_on_down) or (
                        status.is_up and s.alert_on_recovery
                    ):
                        await emit_notification(
                            {
                                "channel": "service",
                                "service_id": s.id,
                                "name": s.name,
                                "slug": s.slug,
                                "is_up": status.is_up,
                                "latency_ms": status.latency_ms,
                                "changed_at": status.last_change_at,
                            }
                        )

        finally:
            db.close()

        await asyncio.sleep(interval_seconds)
