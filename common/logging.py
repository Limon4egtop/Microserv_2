import logging
import sys
from typing import Optional

def setup_logging(service_name: str) -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
