import io
import logging
import os
from datetime import datetime
from typing import List

from scrapers.base import Job

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "hospitality": "🍽️ Hôtellerie / Restauration",
    "tourism": "🗺️ Tourisme",
}

MAX_MSG_LEN = 4000  # Telegram limit is 4096, keep margin


def _escape(text: str) -> str:
    for char in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(char, f"\\{char}")
    return text


def _job_line(job: Job) -> str:
    title = _escape(job.title)
    company = _escape(job.company)
    location = _escape(job.location)
    return f"• [{title}]({job.url}) — {company}, {location}"


def _build_digest(jobs: List[Job], today: str) -> List[str]:
    """Build the full digest as a list of messages respecting Telegram's limit."""
    hospitality = [j for j in jobs if j.category == "hospitality"]
    tourism = [j for j in jobs if j.category == "tourism"]

    lines = [
        f"🇨🇭 *Offres du jour — {_escape(today)}*",
        f"_{len(jobs)} nouveaux postes en Suisse romande_",
        "",
    ]

    for category, cat_jobs in [("hospitality", hospitality), ("tourism", tourism)]:
        if not cat_jobs:
            continue
        label = CATEGORY_LABELS[category]
        lines.append(f"*{_escape(label)} \\({len(cat_jobs)}\\)*")
        for job in cat_jobs:
            lines.append(_job_line(job))
        lines.append("")

    # Split into chunks respecting the 4000 char limit
    messages = []
    current = ""
    for line in lines:
        candidate = current + line + "\n"
        if len(candidate) > MAX_MSG_LEN:
            if current:
                messages.append(current.strip())
            current = line + "\n"
        else:
            current = candidate
    if current.strip():
        messages.append(current.strip())

    return messages


async def send_digest(jobs: List[Job], config: dict) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.error("Telegram credentials missing — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return

    try:
        from telegram import Bot, InputFile  # type: ignore
        from telegram.constants import ParseMode  # type: ignore
    except ImportError:
        logger.error("python-telegram-bot not installed.")
        return

    bot = Bot(token=token)
    today = datetime.now().strftime("%d %B %Y")
    messages = _build_digest(jobs, today)

    for msg in messages:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logger.warning("Telegram send error: %s", exc)

    # Send cover letters as file attachments (only if LLM enabled)
    for job in jobs:
        if job.cover_letter:
            try:
                filename = f"lettre_{job.company.replace(' ', '_')[:30]}.txt"
                content = f"Objet : {job.subject_line}\n\n{job.cover_letter}".encode("utf-8")
                await bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(io.BytesIO(content), filename=filename),
                    caption=f"📝 {job.title} — {job.company}",
                )
            except Exception as exc:
                logger.warning("Telegram file send error for %s: %s", job.id, exc)

    logger.info("Telegram: digest sent (%d jobs, %d messages)", len(jobs), len(messages))
