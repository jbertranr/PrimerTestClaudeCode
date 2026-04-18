"""
Swiss Job Finder — daily run entry point.
Run manually:  python main.py
Run as daemon: python scheduler.py
"""

import asyncio
import logging
import os
import sys
from typing import List

import yaml
from dotenv import load_dotenv

from scrapers.base import Job
from scrapers.jobspy_scraper import JobSpyScraper
from scrapers.jobup_scraper import JobupScraper
from scrapers.jobs_ch_scraper import JobsChScraper
from storage import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rank_jobs(jobs: List[Job], candidate: dict) -> List[Job]:
    """Score jobs by keyword relevance to candidate profile."""
    profile_words = set(
        " ".join(
            candidate.get("skills", []) + candidate.get("experience", [])
        ).lower().split()
    )

    def score(job: Job) -> int:
        desc_words = set(job.description.lower().split())
        return len(profile_words & desc_words)

    return sorted(jobs, key=score, reverse=True)


async def run_daily(config: dict) -> None:
    sources_cfg = config.get("sources", {})
    scrapers = []

    if sources_cfg.get("jobspy", True):
        scrapers.append(JobSpyScraper(config))
    if sources_cfg.get("jobup", True):
        scrapers.append(JobupScraper(config))
    if sources_cfg.get("jobs_ch", True):
        scrapers.append(JobsChScraper(config))

    # Run all scrapers concurrently
    logger.info("Starting scraping from %d source(s)...", len(scrapers))
    results = await asyncio.gather(
        *[s.scrape() for s in scrapers], return_exceptions=True
    )

    all_new_jobs: List[Job] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Scraper error: %s", result)
            continue
        for job in result:
            if db.is_new(job.id):
                db.mark_seen(job)
                all_new_jobs.append(job)

    logger.info("New jobs found: %d", len(all_new_jobs))

    if not all_new_jobs:
        logger.info("No new jobs today — nothing to send.")
        return

    # Optional: generate cover letters via Claude API
    llm_cfg = config.get("llm", {})
    if llm_cfg.get("enabled", False):
        from llm.claude_client import ClaudeClient

        client = ClaudeClient(config)
        ranked = rank_jobs(all_new_jobs, config["candidate"])
        top_n = llm_cfg.get("generate_for_top_n", 5)

        logger.info("Generating cover letters for top %d jobs...", top_n)
        for job in ranked[:top_n]:
            try:
                result = await client.generate_cover_letter(job, config["candidate"])
                job.cover_letter = result.get("letter", "")
                job.subject_line = result.get("subject_line", "")
                if job.cover_letter:
                    db.mark_cover_letter_done(job.id)
                    logger.info("Cover letter generated for: %s @ %s", job.title, job.company)
            except Exception as exc:
                logger.warning("Cover letter generation failed for %s: %s", job.id, exc)
    else:
        logger.info("LLM disabled (set llm.enabled = true in config.yaml to activate)")

    # Send notifications
    notif_cfg = config.get("notifications", {})

    if notif_cfg.get("telegram", {}).get("enabled", False):
        from notifications.telegram_bot import send_digest as tg_send
        await tg_send(all_new_jobs, config)
    else:
        logger.info("Telegram disabled — printing summary to console instead")
        _print_summary(all_new_jobs)

    if notif_cfg.get("email", {}).get("enabled", False):
        from notifications.email_sender import send_digest as email_send
        email_send(all_new_jobs)


def _print_summary(jobs: List[Job]) -> None:
    print(f"\n{'='*60}")
    print(f"  Swiss Job Finder — {len(jobs)} new job(s) found")
    print(f"{'='*60}")
    for job in jobs:
        print(f"\n[{job.source}] {job.title}")
        print(f"  Company  : {job.company}")
        print(f"  Location : {job.location}")
        print(f"  Category : {job.category}")
        print(f"  Posted   : {job.posted_at}")
        print(f"  URL      : {job.url}")
        if job.cover_letter:
            print(f"\n  --- Cover Letter ---\n{job.cover_letter}\n")
    print(f"\n{'='*60}\n")


def main():
    load_dotenv()

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    if not os.path.exists(config_path):
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)

    config = load_config(config_path)
    db.init_db()

    asyncio.run(run_daily(config))


if __name__ == "__main__":
    main()
