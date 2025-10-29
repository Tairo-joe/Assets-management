# Optional APScheduler import
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    CronTrigger = None

from app.routes import send_license_expiry_notifications, send_warranty_expiry_notifications
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_scheduler():
    """Start the background scheduler for notifications."""
    if not SCHEDULER_AVAILABLE:
        logger.warning("APScheduler not available. Skipping scheduler startup.")
        return None
    
    scheduler = BackgroundScheduler()
    
    # Schedule license expiry notifications to run daily at 9:00 AM
    scheduler.add_job(
        func=send_license_expiry_notifications,
        trigger=CronTrigger(hour=9, minute=0),  # 9:00 AM daily
        id='license_expiry_notifications',
        name='License Expiry Notifications',
        replace_existing=True
    )
    
    # Schedule warranty expiry notifications to run daily at 9:30 AM
    scheduler.add_job(
        func=send_warranty_expiry_notifications,
        trigger=CronTrigger(hour=9, minute=30),  # 9:30 AM daily
        id='warranty_expiry_notifications',
        name='Warranty Expiry Notifications',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started successfully")
    
    return scheduler

if __name__ == '__main__':
    # Test the scheduler
    scheduler = start_scheduler()
    print("Scheduler is running. Press Ctrl+C to exit.")
    
    try:
        # Keep the script running
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down scheduler...")
        scheduler.shutdown()
        print("Scheduler shut down successfully.")
