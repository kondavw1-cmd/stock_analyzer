import logging
import traceback
from src.trading.price_monitor import check_intraday_price_alerts
from src.utils.notifications import notify_pipeline_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("IntradayMonitorEngine")


def main():
    logger.info("=== Initializing Intraday Live Price Watcher Engine ===")
    try:
        check_intraday_price_alerts()
        logger.info("=== Intraday Price Check Completed Successfully ===")
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"[Error] Intraday monitor failed: {e}\n{error_trace}", exc_info=True)
        notify_pipeline_status(
            status="FAILURE",
            details=f"Intraday Price Monitor Error: {e}\n\nTraceback:\n{error_trace}",
            is_error=True
        )
        raise


if __name__ == "__main__":
    main()