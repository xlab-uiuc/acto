from dataclasses import dataclass
from typing import Union

from acto.checker.checker import Checker, OracleResult, OracleControlFlow


@dataclass
class ConstantResult(OracleResult):
    expected: OracleControlFlow = OracleControlFlow.ok

    def means(self, control_flow: Union[OracleControlFlow, str])->bool:
        return self.expected == control_flow

class ConstantChecker(Checker):
    name = 'constant'

    def __init__(self, expected: OracleControlFlow = OracleControlFlow.ok, **kwargs):
        super().__init__(**kwargs)
        self.expected = expected

    def _check(self, _, __) -> OracleResult:
        return ConstantResult(self.expected)
