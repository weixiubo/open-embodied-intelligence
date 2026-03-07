from __future__ import annotations

import logging

LOGGER_NAME = "openei"


def get_logger(name: str | None = None) -> logging.Logger:
    logger_name = LOGGER_NAME if name is None else f"{LOGGER_NAME}.{name}"
    return logging.getLogger(logger_name)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger(LOGGER_NAME)
    if root.handlers:
        root.setLevel(level)
        return

    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(level)

