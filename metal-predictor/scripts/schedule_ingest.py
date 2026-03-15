#!/usr/bin/env python3
"""
Daily incremental ingestion scheduler.

Runs the incremental ingest job every day at midnight (local time) so the
Qdrant vector DB stays up to date with the latest Yahoo Finance closing prices
without any manual intervention.

Usage
-----
    uv run python scripts/schedule_ingest.py

The process blocks and logs each scheduled run to stdout.  Run it as a
background service (systemd, supervisor, screen, etc.) alongside the API.

Environment
-----------
All configuration (OPENAI_API_KEY, DATA_PERIOD, etc.) is read from .env in the
project root, exactly like the FastAPI app and the CLI ingest script.
"""

import logging
import os
import sys

# Ensure the project root is importable when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from scripts.ingest import run_incremental_ingest

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scheduled job
# ---------------------------------------------------------------------------

def daily_ingest_job() -> None:
    """Wrapper called by APScheduler — runs incremental ingest and logs outcome."""
    log.info("Scheduled daily ingest starting …")
    try:
        run_incremental_ingest()
        log.info("Scheduled daily ingest completed successfully.")
    except Exception as exc:
        # Log but do NOT re-raise: a failed run should not kill the scheduler
        log.error("Scheduled daily ingest FAILED: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")

    # Fire every day at 00:05 UTC (5 minutes after midnight so Yahoo Finance
    # has time to publish the previous day's closing prices).
    scheduler.add_job(
        daily_ingest_job,
        trigger=CronTrigger(hour=0, minute=5, timezone="UTC"),
        id="daily_metal_ingest",
        name="Daily incremental metal price ingest",
        max_instances=1,          # prevent overlapping runs
        misfire_grace_time=3600,  # tolerate up to 1-hour delay before skipping
    )

    log.info("Scheduler started — daily ingest fires at 00:05 UTC every day.")
    log.info("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")
