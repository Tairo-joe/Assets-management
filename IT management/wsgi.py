from app import create_app
from scheduler import start_scheduler
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

if __name__ == "__main__":
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler thread started")
    
    # Enable hot-reload & debug toolbar in development
    app.run(debug=True)
else:
    # For production deployment (e.g., Gunicorn)
    # Start the scheduler
    scheduler = start_scheduler()
    if scheduler:
        logger.info("Scheduler started for production")
    else:
        logger.info("Scheduler not available - notifications will not be automated")
