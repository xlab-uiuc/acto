
class Snapshot(object):
    def __init__(self, input: dict, cli_result: dict, system_state: dict, operator_log: list):
        self.input = input
        self.cli_result = cli_result
        self.system_state = system_state
        self.operator_log = operator_log

def EmptySnapshot(input: dict):
    return Snapshot(input, {}, {}, [])