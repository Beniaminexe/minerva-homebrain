from __future__ import annotations

import asyncio
from textwrap import dedent
from typing import Any, Dict, Optional

import httpx

from ..config import settings

# Use config-driven API base, defaulting to local dev
API_BASE = settings.api_base_url or "http://localhost:8000"

NOTIFICATION_POLL_INTERVAL = 5.0
NOTIFICATION_FETCH_LIMIT = 20
NOTIFICATION_CONSUMER_ID = "telegram-polling-bot"
TELEGRAM_POLL_TIMEOUT = 25  # seconds


async def register_chat_with_backend(chat: dict) -> None:
    payload = {
        "chat_id": chat["id"],
        "chat_type": chat.get("type", "private"),
        "username": chat.get("username"),
        "title": chat.get("title"),
    }
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_BASE}/integrations/telegram/register", json=payload)


async def send_reminder_with_buttons(
    client: httpx.AsyncClient,
    base_url: str,
    chat_id: int,
    text: str,
    occurrence_id: int,
) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "✅ Done", "callback_data": f"done:{occurrence_id}"},
                    {"text": "⏭ Skip", "callback_data": f"skip:{occurrence_id}"},
                ]
            ]
        },
    }

    await client.post(f"{base_url}/sendMessage", json=payload)


def _build_telegram_base_url() -> str:
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")
    return f"https://api.telegram.org/bot{token}"


async def call_backend_status_today() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/status/today")
    resp.raise_for_status()
    return resp.json()


async def call_backend_reminders() -> list[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/reminders")
    resp.raise_for_status()
    return resp.json()


async def send_message(
    client: httpx.AsyncClient,
    base_url: str,
    chat_id: int,
    text: str,
    parse_mode: Optional[str] = None,
) -> None:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    await client.post(f"{base_url}/sendMessage", json=payload)


def format_today_message(data: Dict[str, Any]) -> str:
    word = data["word_of_day"]
    summary = data["reminders_summary"]
    services = data["services"]
    expr = data["expression"]

    lines: list[str] = []

    lines.append(f"📚 Word of the day: {word['word']}")
    lines.append(word["definition"])
    lines.append("")

    lines.append(
        f"⏰ Reminders: {summary['done']}/{summary['total']} done, "
        f"{summary['pending']} pending, {summary['missed']} missed"
    )
    if summary["next"]:
        lines.append(
            f"➡️ Next: {summary['next']['label']} at {summary['next']['due_at']}"
        )
    lines.append("")

    if services:
        lines.append("🖥️ Services:")
        for s in services:
            status_emoji = "🟢" if s["is_up"] else "🔴"
            lines.append(f"- {status_emoji} {s['name']}")
    else:
        lines.append("🖥️ No services configured.")

    lines.append("")
    lines.append(f"🤖 Minerva: {expr['state']} — {expr['message']}")

    return "\n".join(lines)


def format_reminders_message(reminders: list[Dict[str, Any]]) -> str:
    if not reminders:
        return "No reminders configured yet."

    lines = ["📋 Your reminders:"]

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for r in reminders:
        label = r["label"]
        sk = r["schedule_kind"]
        tod = r["time_of_day"]
        enabled = "✅" if r["enabled"] else "⏸️"

        if sk == "DAILY":
            sched = f"daily at {tod}"
        elif sk == "WEEKLY":
            days = r["days_of_week"] or []
            dn = ", ".join(day_names[d] for d in days) if days else "no days"
            sched = f"weekly on {dn} at {tod}"
        else:
            sched = f"{sk} at {tod}"

        lines.append(f"- {enabled} {label} — {sched}")

    return "\n".join(lines)


async def handle_command(
    client: httpx.AsyncClient,
    base_url: str,
    chat_id: int,
    text: str,
    message: dict,
) -> None:
    if text.startswith("/start"):
        await register_chat_with_backend(message["chat"])
        msg = dedent(
            """
            👋 Hey, I'm Minerva.

            I live in your homelab and I can:
            - show today's overview: /today
            - show your reminders: /reminders

            More commands coming soon.
            """
        ).strip()
        await send_message(client, base_url, chat_id, msg)
        return

    if text.startswith("/today"):
        data = await call_backend_status_today()
        msg = format_today_message(data)
        await send_message(client, base_url, chat_id, msg)
        return

    if text.startswith("/reminders"):
        reminders = await call_backend_reminders()
        msg = format_reminders_message(reminders)
        await send_message(client, base_url, chat_id, msg)
        return

    # default
    await send_message(
        client,
        base_url,
        chat_id,
        "I know /today and /reminders for now.",
    )


async def fetch_pending_notifications(client: httpx.AsyncClient) -> list[dict]:
    url = f"{API_BASE}/notifications/pending"
    params = {
        "limit": NOTIFICATION_FETCH_LIMIT,
        "consumer_id": NOTIFICATION_CONSUMER_ID or "telegram-polling-bot",
        "lock_seconds": 60,
    }
    try:
        resp = await client.get(url, params=params)
    except httpx.RequestError as exc:
        print(f"[telegram_polling] fetch notifications request error ({type(exc).__name__}): {exc!r}")
        raise

    if resp.status_code >= 400:
        detail = ""
        try:
            body = resp.json()
            detail = body.get("detail", "")
        except Exception:
            body = resp.text[:500]
        print(
            f"[telegram_polling] fetch notifications HTTP {resp.status_code} path={resp.request.url.path}; "
            f"detail={detail or 'n/a'}; body={body}"
        )
        resp.raise_for_status()

    try:
        return resp.json()
    except Exception as exc:
        body = resp.text[:500]
        print(f"[telegram_polling] fetch notifications decode error ({type(exc).__name__}): body={body}")
        raise


async def ack_notification(client: httpx.AsyncClient, event_id: int) -> None:
    try:
        await client.post(f"{API_BASE}/notifications/{event_id}/ack")
    except Exception as exc:
        print(f"[telegram_polling] failed to ack notification {event_id}: {exc}")


async def fail_notification(client: httpx.AsyncClient, event_id: int, error: str) -> None:
    try:
        await client.post(
            f"{API_BASE}/notifications/{event_id}/fail",
            json={"error_message": error},
        )
    except Exception as exc:
        print(f"[telegram_polling] failed to record failure for {event_id}: {exc}")


async def deliver_notification(
    client: httpx.AsyncClient,
    base_url: str,
    notif: dict,
) -> None:
    payload = notif.get("payload") or {}
    channel = notif.get("channel") or payload.get("channel")
    if channel != "telegram":
        raise ValueError(f"unsupported channel {channel}")

    chat_id = payload.get("chat_id")
    if not chat_id:
        raise ValueError("missing chat_id")

    occ_id = payload.get("occurrence_id")
    label = payload.get("label")
    due_at = payload.get("due_at")
    text = payload.get("text")

    if not text:
        if label and due_at:
            text = f"⏰ Reminder: {label} at {due_at}"
        elif label:
            text = f"⏰ Reminder: {label}"
        else:
            text = "⏰ Reminder"

    if occ_id is not None:
        await send_reminder_with_buttons(client, base_url, chat_id, text, occ_id)
    else:
        await send_message(client, base_url, chat_id, text, parse_mode=None)


async def process_pending_notifications(
    client: httpx.AsyncClient,
    base_url: str,
) -> None:
    try:
        notifications = await fetch_pending_notifications(client)
    except Exception:
        # fetch already logged details
        return

    for notif in notifications:
        event_id = notif.get("id")
        if not event_id:
            continue
        try:
            await deliver_notification(client, base_url, notif)
        except Exception as exc:
            await fail_notification(client, event_id, str(exc)[:500])
        else:
            await ack_notification(client, event_id)
        await asyncio.sleep(0)  # yield control


async def answer_callback_query(client: httpx.AsyncClient, base_url: str, callback_id: str, text: str) -> None:
    try:
        await client.post(
            f"{base_url}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text},
        )
    except Exception as exc:
        print(f"[telegram_polling] failed to answer callback: {exc}")


async def mark_occurrence(
    client: httpx.AsyncClient,
    occ_id: int,
    action: str,
) -> None:
    url = f"{API_BASE}/occurrences/{occ_id}/{action}"
    resp = await client.post(url)
    resp.raise_for_status()


async def handle_callback_query(
    client: httpx.AsyncClient,
    base_url: str,
    callback_query: dict,
) -> None:
    data = callback_query.get("data") or ""
    callback_id = callback_query.get("id")
    message = callback_query.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    if not data or not callback_id:
        return

    action = None
    occ_id: Optional[int] = None

    if data.startswith("done:"):
        action = "done"
        try:
            occ_id = int(data.split(":", 1)[1])
        except Exception:
            occ_id = None
    elif data.startswith("skip:"):
        action = "skip"
        try:
            occ_id = int(data.split(":", 1)[1])
        except Exception:
            occ_id = None

    if action and occ_id is not None:
        try:
            await mark_occurrence(client, occ_id, action)
            await answer_callback_query(client, base_url, callback_id, f"Marked {action}.")
            if chat_id:
                await send_message(client, base_url, chat_id, f"Reminder {occ_id} {action}.")
        except Exception as exc:
            await answer_callback_query(client, base_url, callback_id, "Failed, try again.")
            print(f"[telegram_polling] failed to mark occurrence {occ_id} {action}: {exc}")
    else:
        await answer_callback_query(client, base_url, callback_id, "Unsupported action.")


async def polling_loop() -> None:
    base_url = _build_telegram_base_url()
    offset: Optional[int] = None
    next_notification_poll = 0.0

    def build_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
            http2=False,
            transport=httpx.AsyncHTTPTransport(retries=3),
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=10),
        )

    loop = asyncio.get_running_loop()
    first_run = True

    while True:
        try:
            async with build_client() as client:
                # Optional startup check to confirm bot identity (only once)
                if first_run:
                    try:
                        resp = await client.get(f"{base_url}/getMe")
                        resp.raise_for_status()
                        data = resp.json()
                        username = data.get("result", {}).get("username")
                        print(f"[telegram_polling] bot connected as @{username or 'unknown'}")
                    except Exception as exc:
                        status = None
                        desc = ""
                        if isinstance(exc, httpx.HTTPStatusError):
                            status = exc.response.status_code
                            try:
                                desc = exc.response.json().get("description", "")
                            except Exception:
                                desc = exc.response.text[:200]
                        print(f"[telegram_polling] getMe failed (status={status}): {type(exc).__name__}: {desc or exc}")
                        return
                    # Backend reachability check
                    try:
                        print(f"[telegram_polling] API base: {API_BASE}")
                        resp_backend = await client.get(
                            f"{API_BASE}/notifications/pending",
                            params={
                                "limit": 1,
                                "consumer_id": NOTIFICATION_CONSUMER_ID or "telegram-polling-bot",
                                "lock_seconds": 1,
                            },
                        )
                        if resp_backend.status_code >= 400:
                            try:
                                body = resp_backend.json()
                                detail = body.get("detail", "")
                            except Exception:
                                body = resp_backend.text[:200]
                                detail = ""
                            print(
                                f"[telegram_polling] backend check HTTP {resp_backend.status_code} path={resp_backend.request.url.path}; "
                                f"detail={detail or 'n/a'}; body={body}"
                            )
                        else:
                            print("[telegram_polling] backend notifications endpoint reachable")
                    except Exception as exc:
                        print(f"[telegram_polling] backend check error ({type(exc).__name__}): {exc}")
                    first_run = False

                while True:
                    params: Dict[str, Any] = {
                        "timeout": TELEGRAM_POLL_TIMEOUT,
                    }
                    if offset is not None:
                        params["offset"] = offset

                    try:
                        resp = await client.get(f"{base_url}/getUpdates", params=params)
                        if resp.status_code != 200:
                            try:
                                body = resp.json()
                                desc = body.get("description", "")
                            except Exception:
                                body = resp.text[:200]
                                desc = ""
                            print(
                                f"[telegram_polling] getUpdates HTTP {resp.status_code}; "
                                f"description={desc or 'n/a'}; body={body}"
                            )
                            await asyncio.sleep(5)
                            continue
                        data = resp.json()
                    except httpx.ReadError as exc:
                        print(f"[telegram_polling] getUpdates read error ({type(exc).__name__}): {exc}")
                        break  # recreate client
                    except httpx.RequestError as exc:
                        print(f"[telegram_polling] getUpdates request error ({type(exc).__name__}): {exc}")
                        break  # recreate client
                    except Exception as exc:
                        print(f"[telegram_polling] error calling getUpdates: {type(exc).__name__}: {exc}")
                        await asyncio.sleep(5)
                        continue

                    for update in data.get("result", []):
                        offset = update["update_id"] + 1

                        # Handle callback queries first
                        callback_query = update.get("callback_query")
                        if callback_query:
                            await handle_callback_query(client, base_url, callback_query)
                            continue

                        message = update.get("message")
                        if not message:
                            continue

                        chat = message.get("chat", {})
                        chat_id = chat.get("id")
                        text = message.get("text") or ""

                        if not chat_id or not text:
                            continue

                        await handle_command(client, base_url, chat_id, text.strip(), message)

                    now = loop.time()
                    if now >= next_notification_poll:
                        await process_pending_notifications(client, base_url)
                        next_notification_poll = now + NOTIFICATION_POLL_INTERVAL
        except Exception as exc:
            print(f"[telegram_polling] client loop error ({type(exc).__name__}): {exc}")

        # Recreate client after transient failure
        await asyncio.sleep(2)


async def main() -> None:
    print("Starting Minerva Telegram polling bot...")
    await polling_loop()


if __name__ == "__main__":
    asyncio.run(main())
