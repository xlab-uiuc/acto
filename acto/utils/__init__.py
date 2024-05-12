from .early_stop import *
from .error_handler import *
from .k8s_helper import *
from .preprocess import *
from .thread_logger import get_thread_logger


def is_prefix(prefix: list, path: list) -> bool:
    '''Checks if subpath is a subfield of path
    '''
    if len(path) < len(prefix):
        return False
    for i in range(len(prefix)):
        if isinstance(path[i], int):
            continue
        if path[i] != prefix[i]:
            return False
    return True