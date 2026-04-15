"""
Job Scheduler for periodic scraping runs
"""

import asyncio
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.database import db
from app.scraper.scraper_engine import scraper_engine
from app.utils.logger import get_logger

logger = get_logger()

class JobScheduler:
    """Scheduler for running scraping jobs periodically"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._running = False
    
    def start(self):
        """Start the scheduler"""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Job scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Job scheduler stopped")
    
    def schedule_job(self, job_id: str, cron_expression: Optional[str] = None, 
                   interval_minutes: Optional[int] = None):
        """Schedule a job to run periodically"""
        if cron_expression:
            trigger = CronTrigger.from_crontab(cron_expression)
        elif interval_minutes:
            trigger = IntervalTrigger(minutes=interval_minutes)
        else:
            logger.error("Either cron_expression or interval_minutes must be provided")
            return
        
        # Remove existing job if any
        self.scheduler.remove_job(job_id)
        
        # Add new job
        self.scheduler.add_job(
            self._run_scheduled_job,
            trigger=trigger,
            id=job_id,
            args=[job_id],
            name=f"Scheduled job: {job_id}"
        )
        logger.info(f"Scheduled job {job_id} with trigger: {trigger}")
    
    def unschedule_job(self, job_id: str):
        """Remove a scheduled job"""
        if self.scheduler.remove_job(job_id):
            logger.info(f"Unscheduled job {job_id}")
        else:
            logger.warning(f"Job {job_id} was not scheduled")
    
    def _run_scheduled_job(self, job_id: str):
        """Run a scheduled job"""
        try:
            job = db.get_job(job_id)
            if not job:
                logger.error(f"Scheduled job not found: {job_id}")
                return
            
            logger.info(f"Running scheduled job: {job.name}")
            asyncio.run(scraper_engine.run_job(job))
            logger.info(f"Completed scheduled job: {job.name}")
            
        except Exception as e:
            logger.error(f"Error running scheduled job {job_id}: {e}")

# Global scheduler instance
job_scheduler = JobScheduler()