import logging
import threading
from typing import Union


class PrefixLoggerAdapter(logging.LoggerAdapter):
    """A logger adapter that adds a prefix to every message"""

    def process(self, msg: str, kwargs) -> tuple[str, dict]:
        """Add the prefix to the message"""
        if self.extra is not None and "prefix" in self.extra:
            return (f'[{self.extra["prefix"]}] {msg}', kwargs)
        return (msg, kwargs)


logger_prefix = threading.local()


def set_thread_logger_prefix(prefix: str) -> None:
    """
    Store the prefix in the thread local storag,
    invoke get_thread_logger_with_prefix to get the updated logger
    """
    logger_prefix.prefix = prefix


def get_thread_logger(
    with_prefix: bool = True,
) -> Union[logging.LoggerAdapter, logging.Logger]:
    """Get the logger with the prefix from the thread local storage"""
    logger = logging.getLogger(threading.current_thread().name)
    logger.setLevel(logging.DEBUG)
    # if the prefix is not set, return the original logger
    if not with_prefix or not hasattr(logger_prefix, "prefix"):
        return logger

    return PrefixLoggerAdapter(logger, extra={"prefix": logger_prefix.prefix})
