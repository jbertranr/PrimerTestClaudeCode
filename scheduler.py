"""
Long-running daemon that fires main.run_daily() on a daily schedule.
Usage:  python scheduler.py
        python scheduler.py config.yaml   (custom config path)
"""

import asyncio
import logging
import os
import sys

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from main import load_config, run_daily
from storage import database as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scheduler")


async def scheduled_run(config: dict) -> None:
    logger.info("Scheduled run starting...")
    try:
        await run_daily(config)
    except Exception as exc:
        logger.error("Scheduled run failed: %s", exc)


async def main():
    load_dotenv()

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = load_config(config_path)
    db.init_db()

    schedule_cfg = config.get("schedule", {})
    hour = schedule_cfg.get("hour", 8)
    minute = schedule_cfg.get("minute", 0)
    timezone = schedule_cfg.get("timezone", "Europe/Zurich")

    scheduler = AsyncIOScheduler(timezone=timezone)
    scheduler.add_job(
        scheduled_run,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=timezone),
        args=[config],
        id="daily_job_finder",
        replace_existing=True,
    )
    scheduler.start()

    logger.info(
        "Scheduler started — will run daily at %02d:%02d (%s). Press Ctrl+C to stop.",
        hour, minute, timezone
    )

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(main())
