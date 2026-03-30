import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.infrastructure.scheduler.disclosure_jobs import (
    job_incremental_collect,
    job_refresh_company_list,
    job_process_documents,
    job_cleanup_expired_data,
    job_seasonal_quarterly,
    job_seasonal_semiannual,
    job_seasonal_annual,
)

logger = logging.getLogger(__name__)


def create_disclosure_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    # -- Hourly collection --

    # Every hour at :00 — incremental disclosure collection
    scheduler.add_job(
        job_incremental_collect,
        trigger=CronTrigger(minute=0),
        id="incremental_collect",
        name="Incremental disclosure collection",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # -- Daily operations --

    # Daily 02:00 — refresh company list (DART + Naver Finance)
    scheduler.add_job(
        job_refresh_company_list,
        trigger=CronTrigger(hour=2, minute=0),
        id="refresh_company_list",
        name="Refresh company list",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Daily 02:30 — process core disclosure documents (DART raw -> summary + RAG chunks)
    scheduler.add_job(
        job_process_documents,
        trigger=CronTrigger(hour=2, minute=30),
        id="process_documents",
        name="Process disclosure documents (summary + RAG)",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Daily 03:00 — clean up expired data
    scheduler.add_job(
        job_cleanup_expired_data,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_expired_data",
        name="Clean up expired data",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # -- Seasonal report collection --

    # Quarterly report (A003): Mar, May, Aug, Nov 15th at 04:00
    scheduler.add_job(
        job_seasonal_quarterly,
        trigger=CronTrigger(month="3,5,8,11", day=15, hour=4, minute=0),
        id="seasonal_quarterly",
        name="Quarterly report seasonal collection",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Semi-annual report (A002): Mar, Sep 15th at 04:30
    scheduler.add_job(
        job_seasonal_semiannual,
        trigger=CronTrigger(month="3,9", day=15, hour=4, minute=30),
        id="seasonal_semiannual",
        name="Semi-annual report seasonal collection",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Annual report (A001): Mar, Apr 1st at 05:00
    scheduler.add_job(
        job_seasonal_annual,
        trigger=CronTrigger(month="3,4", day=1, hour=5, minute=0),
        id="seasonal_annual",
        name="Annual report seasonal collection",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info("Disclosure scheduler configured (7 jobs: 1 hourly, 3 daily, 3 seasonal)")
    return scheduler
