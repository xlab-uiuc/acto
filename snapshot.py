
class Snapshot(object):
    def __init__(self, input: dict, cli_result: dict, system_state: dict, operator_log: list, field_val_dict: dict):
        self.input = input
        self.cli_result = cli_result
        self.system_state = system_state
        self.operator_log = operator_log
        self.field_val_dict = field_val_dict

def EmptySnapshot(input: dict):
    return Snapshot(input, {}, {}, [], {})