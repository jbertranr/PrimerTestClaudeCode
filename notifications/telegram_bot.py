import io
import logging
import os
from datetime import datetime
from typing import List

from scrapers.base import Job

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "hospitality": "Hôtellerie / Restauration",
    "tourism": "Tourisme",
}


def _escape(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    for char in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(char, f"\\{char}")
    return text


def _job_card(job: Job) -> str:
    cat = CATEGORY_LABELS.get(job.category, job.category)
    title = _escape(job.title)
    company = _escape(job.company)
    location = _escape(job.location)
    source = _escape(job.source)
    posted = _escape(job.posted_at)

    return (
        f"*{title}*\n"
        f"🏢 {company}\n"
        f"📍 {location}\n"
        f"🏷️ {cat} \\| 📅 {posted} \\| 🔗 {source}\n"
        f"[Voir l'offre]({job.url})"
    )


async def send_digest(jobs: List[Job], config: dict) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.error(
            "Telegram credentials missing — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
        )
        return

    try:
        from telegram import Bot, InputFile  # type: ignore
        from telegram.constants import ParseMode  # type: ignore
    except ImportError:
        logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return

    bot = Bot(token=token)
    today = datetime.now().strftime("%d %B %Y")
    hospitality = [j for j in jobs if j.category == "hospitality"]
    tourism = [j for j in jobs if j.category == "tourism"]
    with_letters = [j for j in jobs if j.cover_letter]

    # --- Daily summary header ---
    summary = (
        f"*Rapport quotidien — {_escape(today)}*\n\n"
        f"✅ Nouveaux postes trouvés : *{len(jobs)}*\n"
        f"  🍽️ Hôtellerie/Restauration : {len(hospitality)}\n"
        f"  🗺️ Tourisme : {len(tourism)}\n"
        f"  📝 Lettres de motivation générées : {len(with_letters)}\n"
    )
    await bot.send_message(chat_id=chat_id, text=summary, parse_mode=ParseMode.MARKDOWN_V2)

    max_jobs = config.get("notifications", {}).get("telegram", {}).get("max_jobs_per_digest", 30)

    for job in jobs[:max_jobs]:
        try:
            card_text = _job_card(job)
            await bot.send_message(
                chat_id=chat_id,
                text=card_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=False,
            )

            if job.cover_letter:
                filename = (
                    f"lettre_{job.company.replace(' ', '_')[:30]}.txt"
                )
                content = (
                    f"Objet : {job.subject_line}\n\n"
                    f"{job.cover_letter}"
                ).encode("utf-8")
                await bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(io.BytesIO(content), filename=filename),
                    caption=f"📝 Lettre de motivation — {job.title} @ {job.company}",
                )

        except Exception as exc:
            logger.warning("Telegram send error for job %s: %s", job.id, exc)

    logger.info("Telegram: digest sent (%d jobs)", len(jobs[:max_jobs]))
