"""
Functions with no dependencies on other acto modules.
"""


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
