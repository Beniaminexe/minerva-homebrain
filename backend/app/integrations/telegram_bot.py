from __future__ import annotations

import asyncio
from textwrap import dedent

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from ..config import settings


API_BASE = "http://localhost:8000"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = dedent(
        """
        👋 Hey, I'm Minerva.

        Commands:
        /today — today's overview
        /reminders — list reminders
        """
    ).strip()
    await update.message.reply_text(text)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/status/today")
    resp.raise_for_status()
    data = resp.json()

    word = data["word_of_day"]
    summary = data["reminders_summary"]
    services = data["services"]
    expr = data["expression"]

    lines = []
    lines.append(f"📚 *Word of the day:* _{word['word']}_")
    lines.append(word["definition"])
    lines.append("")

    lines.append(f"⏰ Reminders: {summary['done']}/{summary['total']} done")
    if summary["next"]:
        lines.append(f"➡ Next: *{summary['next']['label']}*")
    lines.append("")

    lines.append("🖥 *Services:*")
    for s in services:
        status_emoji = "🟢" if s["is_up"] else "🔴"
        lines.append(f"{status_emoji} {s['name']}")

    lines.append("")
    lines.append(f"😶 Minerva: {expr['state']} — {expr['message']}")

    await update.message.reply_markdown("\n".join(lines))


async def cmd_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/reminders")
    resp.raise_for_status()
    reminders = resp.json()

    if not reminders:
        await update.message.reply_text("No reminders yet.")
        return

    lines = ["📋 *Your reminders:*"]
    for r in reminders:
        label = r["label"]
        tod = r["time_of_day"]
        lines.append(f"• {label} at {tod}")

    await update.message.reply_markdown("\n".join(lines))


async def main() -> None:
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

    application = (
        Application.builder()
        .token(token)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("today", cmd_today))
    application.add_handler(CommandHandler("reminders", cmd_reminders))

    print("Starting Minerva Telegram Bot…")
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
