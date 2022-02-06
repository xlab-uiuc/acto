import sys, os, inspect
import enum

class RunResult(enum.Enum):
    passing = 0
    invalidInput = 1
    error = 2
    unchanged = 3


def p_print(msg: str):
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    filename            = os.path.basename(caller.filename)
    line_number         = caller.lineno
    print('%s:%d:\t%s' % (filename, line_number, msg), file=sys.stdout)


def p_debug(msg: str):
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    filename            = os.path.basename(caller.filename)
    line_number         = caller.lineno
    print('%s:%d:\t%s' % (filename, line_number, msg), file=sys.stderr)


def p_error(msg: str):
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    filename            = os.path.basename(caller.filename)
    line_number         = caller.lineno
    print('%s:%d:\t%s' % (filename, line_number, msg), file=sys.stderr)