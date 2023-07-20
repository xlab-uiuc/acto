import re
from dataclasses import dataclass, field

from acto.snapshot import Snapshot

from acto.checker.checker import Checker, OracleResult
from typing import List

from frozenlist import FrozenList

java_exception_regex = re.compile(r'(^\S.*$)\n((?:^\s+at .*$\n?)+)', flags=re.MULTILINE)


@dataclass(frozen=True, eq=True)
class JavaException:
    reason: str
    stack: FrozenList


@dataclass
class JavaExceptionLogResult(OracleResult):
    operator_exceptions: List[JavaException] = field(default_factory=list)

    def __post_init__(self):
        if self.operator_exceptions:
            self.message = f'A Java exception occurred in the operator, {self.operator_exceptions[0].reason}'


def regex_match_to_java_exception(reason: str, stack: str):
    stacks = FrozenList(map(lambda line: line.strip(), stack.split('\n')))
    stacks.freeze()
    return JavaException(reason.strip(), stacks)


class JavaExceptionLogChecker(Checker):
    name = 'java_log'

    def _check(self, snapshot: Snapshot, _: Snapshot) -> OracleResult:
        exceptions = java_exception_regex.findall('\n'.join(snapshot.operator_log))
        exceptions = set(map(lambda e: regex_match_to_java_exception(*e), exceptions))
        return JavaExceptionLogResult(operator_exceptions=list(exceptions))
