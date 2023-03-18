import json
import re
from typing import Dict, List, Tuple

import yaml


class InputSignature:

    def __init__(self, field=None) -> None:
        self.field = field if field != None else None


class Field:

    def __init__(self, regex: str) -> None:
        self.regex = regex if regex != None else None

    def match(self, value: str) -> bool:
        return re.match(self.regex, value)


class StateResult:

    def __init__(self, field: Dict = None, prev=None, curr=None, p: bool = False) -> None:
        self.field = Field(**field) if field != None else None
        self.prev = prev if prev != None else None
        self.curr = curr if curr != None else None
        self.p = p if p != None else False

    def match(self, value: Dict) -> bool:
        if self.p != False and isinstance(value, str) and value != 'Pass':
            return False
        if self.field != None and not self.field.match(json.dumps(value['input_delta']['path'])):
            return False
        if self.prev != None and self.prev != value['prev']:
            return False
        if self.curr != None and self.curr != value['curr']:
            return False
        return True


class TypeChange:

    def __init__(self, field: Dict = None, old_type=None, new_type=None) -> None:
        self.field = Field(**field) if field != None else None
        self.prev = old_type if old_type != None else None
        self.curr = new_type if new_type != None else None

    def match(self, value: Dict) -> bool:
        if self.field != None and not self.field.match(json.dumps(value['dictionary_item_added'])):
            return False
        if self.prev != None and self.prev != value['prev']:
            return False
        if self.curr != None and self.curr != value['curr']:
            return False
        return True


class RecoveryDelta:

    def __init__(self, dictionary_item_added: List = None, type_changes: List = None):
        self.dictionary_item_added = [Field(**i) for i in dictionary_item_added
                                     ] if dictionary_item_added != None else None
        self.type_changes = [TypeChange(**i) for i in type_changes
                            ] if type_changes != None else None

    def match(self, value: Dict) -> bool:
        if self.dictionary_item_added != None:
            for field in self.dictionary_item_added:
                if not field.match(json.dumps(value['dictionary_item_added'])):
                    return False
        return True


class RecoveryResult:

    def __init__(self, delta: Dict) -> None:
        self.delta = RecoveryDelta(**delta) if delta != None else None

    def match(self, value: Dict) -> bool:
        if self.delta != None and not self.delta.match(value):
            return False
        return True


class SymptomSignature:

    def __init__(self,
                 state_result: Dict = None,
                 health_result: bool = None,
                 recovery_result: Dict = None) -> None:
        self.system_result = StateResult(**state_result) if state_result != None else None
        self.health_result = health_result if health_result != None else None
        self.recovery_result = RecoveryResult(
            **recovery_result) if recovery_result != None else None

    def match(self, value: Dict) -> bool:
        if self.system_result != None and not self.system_result.match(value):
            return False
        if self.health_result != None:
            if self.health_result and value['health_result'] != 'Pass':
                return False
            if not self.health_result and value['health_result'] == 'Pass':
                return False
        if self.recovery_result != None and not self.recovery_result.match(value):
            return False


class Signature:

    def __init__(self,
                 input: InputSignature = None,
                 symptoms: List[SymptomSignature] = None) -> None:
        self.input = InputSignature(**input) if input != None else None
        self.symptoms = [SymptomSignature(**i) for i in symptoms] if symptoms != None else None

    def match(self, value: Dict) -> bool:
        if self.input != None and not self.input.match(value['input']):
            return False
        if self.symptoms != None:
            for symptom in self.symptoms:
                if not symptom.match(value['symptom']):
                    return False
        return True


class Bug:

    def __init__(self, name: str, signatures: List) -> None:
        self.name = name
        self.signatures = [Signature(**i) for i in signatures]

    def match(self, value: Dict) -> bool:
        for signature in self.signatures:
            if signature.match(value):
                return True
        return False


class FalsePositive:

    def __init__(self, name: str, field: Dict = None) -> None:
        self.name = name
        self.field = Field(**field)

    pass


class ControlFlowFP(FalsePositive):

    def __init__(self, name: str, field: Dict = None, type: str = None) -> None:
        self.name = name
        self.field = Field(**field)

    def match(self, value: Dict) -> bool:
        if self.field != None and not self.field.match(json.dumps(value['input_delta']['path'])):
            return False
        return True


def FalsePositiveFactory(**argv) -> FalsePositive:
    if argv['type'] == 'control-flow':
        return ControlFlowFP(**argv)
    else:
        raise ValueError(f'Unknown false positive type: {argv["type"]}')


class Misconfiguration:

    def __init__(self, name: str, signatures: List) -> None:
        self.name = name
        self.signatures = [Signature(**i) for i in signatures]

    def match(self, value: Dict) -> bool:
        for signature in self.signatures:
            if signature.match(value):
                return True
        return False


class Rules:

    def __init__(self, bugs: List[Bug], false_positives: List[FalsePositive],
                 misconfigurations: List[Misconfiguration]) -> None:
        self.bugs = [Bug(**i) for i in bugs]
        self.false_positives = [FalsePositiveFactory(**i) for i in false_positives]
        self.misconfigurations = [Misconfiguration(**i) for i in misconfigurations]

    def match(self, value: Dict) -> Tuple[bool, str]:
        for bug in self.bugs:
            if bug.match(value):
                return (False, bug.name)
        for misconfiguration in self.misconfigurations:
            if misconfiguration.match(value):
                return (False, misconfiguration.name)
        for false_positive in self.false_positives:
            if false_positive.match(value):
                return (True, false_positive)
        return None


def classify_alarm(result: dict) -> Tuple[str, str]:
    with open('data/cass-operator/inspection.yaml', 'r') as f:
        rule_file = yaml.load(f, Loader=yaml.FullLoader)
    rules = Rules(**rule_file)
    match = rules.match(result)
    pass


if __name__ == '__main__':
    classify_alarm({})