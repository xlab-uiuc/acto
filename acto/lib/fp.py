from functools import wraps
from typing import Callable


def drop_first_parameter(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args[1:], **kwargs)

    return wrapper

def create_constant_function(x):
    def constant_function(*_, **__):
        return x
    return constant_function

def unreachable(*_, **__):
    assert False, 'Unreachable'