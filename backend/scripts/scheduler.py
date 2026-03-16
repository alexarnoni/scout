"""
Scheduler diário: sincroniza jogos do dia anterior às 00:30 (America/Sao_Paulo).

Por que 00:30 e não meia-noite: jogos do Brasileirão podem terminar ~23h30,
então esperar 30 minutos garante que o placar e stats finais estão disponíveis
na API antes de sincronizar.

Rodar: python -m scripts.scheduler
Manter vivo via supervisord, systemd, ou container com restart policy.
"""
from __future__ import annotations

import datetime
import logging
import os
import traceback
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)

from app.core.config import DATABASE_URL  # noqa: E402 — after load_dotenv
from app.providers import ESPNProvider  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# Import persistence logic from sync_date — no logic duplication
from scripts.sync_date import process_date_matches  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# competition_id configurable via env — default 1 keeps zero-config local dev working
_COMPETITION_ID = int(os.environ.get("SCOUT_COMPETITION_ID", "1"))

_TIMEZONE = "America/Sao_Paulo"


def sync_yesterday() -> None:
    """Fetch and persist ESPN matches for yesterday.

    Called by the scheduler at 00:30 BRT. Any unhandled exception is caught
    at the call site so the scheduler stays alive for future runs.
    """
    date = datetime.date.today() - datetime.timedelta(days=1)
    logger.info("Starting sync for %s (competition_id=%s)", date, _COMPETITION_ID)

    provider = ESPNProvider()
    matches = provider.fetch_matches_by_date(date)

    if not matches:
        # Normal on rest days — not an error
        logger.info("No matches found for %s, nothing to persist.", date)
        return

    logger.info("%d match(es) found for %s", len(matches), date)

    with SessionLocal() as db:
        counters = process_date_matches(
            db,
            _COMPETITION_ID,
            matches,
            include_players=True,
            verbose=False,
        )
        db.commit()

    logger.info(
        "Sync complete for %s: "
        "matches_inserted=%s matches_updated=%s "
        "stats_inserted=%s stats_updated=%s stats_skipped=%s "
        "players_created=%s player_stats_inserted=%s player_stats_updated=%s",
        date,
        counters["inserted_matches"],
        counters["updated_matches"],
        counters["inserted_stats"],
        counters["updated_stats"],
        counters["skipped_stats"],
        counters["inserted_players"],
        counters["inserted_player_stats"],
        counters["updated_player_stats"],
    )


def _job_with_guard() -> None:
    """Wrapper that catches all exceptions so a failed job never kills the scheduler."""
    try:
        sync_yesterday()
    except Exception:
        # Log full traceback — operator needs this to diagnose failures
        logger.error("sync_yesterday failed:\n%s", traceback.format_exc())


def main() -> None:
    scheduler = BlockingScheduler(timezone=_TIMEZONE)

    # CronTrigger is explicit about intent — cron("30 0 * * *") is unambiguous
    trigger = CronTrigger(hour=0, minute=30, timezone=_TIMEZONE)
    scheduler.add_job(_job_with_guard, trigger, id="sync_yesterday")

    logger.info("Scheduler iniciado. Sync agendado para 00:30 (America/Sao_Paulo).")
    scheduler.start()


if __name__ == "__main__":
    main()
