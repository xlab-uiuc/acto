from functools import wraps
from typing import Callable


def drop_first_parameter(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args[1:], **kwargs)

    return wrapper
