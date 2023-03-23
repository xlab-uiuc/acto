
class Snapshot(object):
    def __init__(self, input: dict, cli_result: dict, system_state: dict, operator_log: list):
        self.input = input
        self.cli_result = cli_result
        self.system_state = system_state
        self.operator_log = operator_log

    def to_dict(self):
        return {
            'input': self.input,
            'cli_result': self.cli_result,
            'system_state': self.system_state,
            'operator_log': self.operator_log
        }

def EmptySnapshot(input: dict):
    return Snapshot(input, {}, {}, [])