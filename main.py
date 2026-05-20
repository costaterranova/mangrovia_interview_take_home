import logging
import signal
import sys

import db
from config import settings
from telegram_handler import build_application


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    db.init_db()
    logger.info("Database initialised at %s", settings.DATABASE_PATH)

    app = build_application()

    def _shutdown(signum, frame):
        logger.info("Received signal %s, shutting down", signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("Bot starting — polling for messages in chat %s", settings.TELEGRAM_CHAT_ID)
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
