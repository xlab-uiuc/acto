"""Error handler for acto, which is used to notify the crash to google form."""
import socket
import sys
import threading
import traceback

import requests

from acto.acto_config import ACTO_CONFIG
from acto.utils.thread_logger import get_thread_logger


def notify_crash(exception: str):
    """Notify the crash to google form"""
    logger = get_thread_logger(with_prefix=True)

    hostname = socket.gethostname()

    url = (
        "https://docs.google.com/forms/d/"
        + "1Hxjg8TDKqBf_47H9gyP63gr3JVCGFwyqxUtSFA7OXhk/formResponse"
    )
    form_data = {
        "entry.471699079": exception,
        "entry.1614228781": f"{sys.argv}",
        "entry.481598949": hostname,
    }
    user_agent = {
        "Referer": "https://docs.google.com/forms/d/"
        + "1Hxjg8TDKqBf_47H9gyP63gr3JVCGFwyqxUtSFA7OXhk/viewform",
        "User-Agent": "Mozilla/5.0 (X11; Linux i686)"
        + " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36",
    }
    _ = requests.post(url, data=form_data, headers=user_agent, timeout=10)
    logger.info("Send notify to google form")


def handle_excepthook(typ, message, stack):
    """Custom exception handler

    Print detailed stack information with local variables
    """
    logger = get_thread_logger(with_prefix=True)

    if issubclass(typ, KeyboardInterrupt):
        sys.__excepthook__(typ, message, stack)
        return

    if ACTO_CONFIG.notifications.enabled:
        notify_crash(f"An exception occured: {typ}: {message}.")

    stack_info = traceback.StackSummary.extract(
        traceback.walk_tb(stack), capture_locals=True
    ).format()
    logger.critical("An exception occured: %s: %s.", typ, message)
    for i in stack_info:
        logger.critical(i.encode().decode("unicode-escape"))
    return


def thread_excepthook(args):
    """Exception notifier for threads"""
    logger = get_thread_logger(with_prefix=True)

    exc_type = args.exc_type
    exc_value = args.exc_value
    exc_traceback = args.exc_traceback
    _ = args.thread
    if issubclass(exc_type, KeyboardInterrupt):
        threading.__excepthook__(args)
        return

    if ACTO_CONFIG.notifications.enabled:
        notify_crash(f"An exception occured: {exc_type}: {exc_value}.")

    stack_info = traceback.StackSummary.extract(
        traceback.walk_tb(exc_traceback), capture_locals=True
    ).format()
    logger.critical("An exception occured: %s: %s.", exc_type, exc_value)
    for i in stack_info:
        logger.critical(i.encode().decode("unicode-escape"))
    return
