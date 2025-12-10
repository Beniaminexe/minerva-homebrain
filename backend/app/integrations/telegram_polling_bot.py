from __future__ import annotations

import asyncio
from textwrap import dedent
from typing import Any, Dict, Optional

import httpx

from ..config import settings


API_BASE = "http://localhost:8000"


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

    lines.append(f"📚 *Word of the day:* _{word['word']}_")
    lines.append(word["definition"])
    lines.append("")

    lines.append(
        f"⏰ Reminders: {summary['done']}/{summary['total']} done, "
        f"{summary['pending']} pending, {summary['missed']} missed"
    )
    if summary["next"]:
        lines.append(
            f"➡ Next: *{summary['next']['label']}* at {summary['next']['due_at']}"
        )
    lines.append("")

    if services:
        lines.append("🖥 *Services:*")
        for s in services:
            status_emoji = "🟢" if s["is_up"] else "🔴"
            lines.append(f"- {status_emoji} {s['name']}")
    else:
        lines.append("🖥 No services configured.")

    lines.append("")
    lines.append(f"😶 Minerva: *{expr['state']}* — {expr['message']}")

    return "\n".join(lines)


def format_reminders_message(reminders: list[Dict[str, Any]]) -> str:
    if not reminders:
        return "No reminders configured yet."

    lines = ["📋 *Your reminders:*"]

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for r in reminders:
        label = r["label"]
        sk = r["schedule_kind"]
        tod = r["time_of_day"]
        enabled = "✅" if r["enabled"] else "⏸"

        if sk == "DAILY":
            sched = f"daily at {tod}"
        elif sk == "WEEKLY":
            days = r["days_of_week"] or []
            dn = ", ".join(day_names[d] for d in days) if days else "no days"
            sched = f"weekly on {dn} at {tod}"
        else:
            sched = f"{sk} at {tod}"

        lines.append(f"- {enabled} *{label}* — {sched}")

    return "\n".join(lines)


async def handle_command(
    client: httpx.AsyncClient,
    base_url: str,
    chat_id: int,
    text: str,
) -> None:
    if text.startswith("/start"):
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
        await send_message(client, base_url, chat_id, msg, parse_mode="Markdown")
        return

    if text.startswith("/reminders"):
        reminders = await call_backend_reminders()
        msg = format_reminders_message(reminders)
        await send_message(client, base_url, chat_id, msg, parse_mode="Markdown")
        return

    # default
    await send_message(
        client,
        base_url,
        chat_id,
        "I know /today and /reminders for now.",
    )


async def polling_loop() -> None:
    base_url = _build_telegram_base_url()
    offset: Optional[int] = None

    async with httpx.AsyncClient(timeout=35.0) as client:
        while True:
            params: Dict[str, Any] = {
                "timeout": 30,
            }
            if offset is not None:
                params["offset"] = offset

            try:
                resp = await client.get(f"{base_url}/getUpdates", params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                print(f"[telegram_polling] error calling getUpdates: {exc}")
                await asyncio.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat = message.get("chat", {})
                chat_id = chat.get("id")
                text = message.get("text") or ""

                if not chat_id or not text:
                    continue

                await handle_command(client, base_url, chat_id, text.strip())


async def main() -> None:
    print("Starting Minerva Telegram polling bot...")
    await polling_loop()


if __name__ == "__main__":
    asyncio.run(main())
