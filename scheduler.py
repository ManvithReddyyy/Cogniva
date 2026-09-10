import time
import logging
from datetime import datetime
from app.daily_runner import run_daily_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

INTERVAL_MINUTES = 10


def run_scheduler():
    logger.info(f"Cogniva Scheduler started.")
    logger.info(f"Running every {INTERVAL_MINUTES} minutes continuously.")

    while True:
        logger.info("=" * 60)
        logger.info(f"Triggering 10-minute pipeline run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        try:
            run_daily_pipeline(hours=24, top_n=5)
        except Exception as e:
            logger.error(f"Error during scheduled run: {e}", exc_info=True)

        logger.info(f"Run completed. Next check in {INTERVAL_MINUTES} minutes...")
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    run_scheduler()
