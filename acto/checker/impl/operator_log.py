from acto.checker.checker import Checker
from acto.common import OracleResult, PassResult, InvalidInputResult, invalid_input_message, ErrorResult, Oracle
from acto.config import actoConfig
from acto.parse_log import parse_log
from acto.snapshot import Snapshot
from acto.lib.dict import visit_dict


class OperatorLogChecker(Checker):
    name = 'log'

    def check(self, _: int, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        input_delta, _ = snapshot.delta(prev_snapshot)

        for line in snapshot.operator_log:
            parsed_log = parse_log(line)
            # We do not check the log line if it is not a warn/error/fatal message
            _, level = visit_dict(parsed_log, ['level'])
            if level not in ['warn', 'error', 'fatal']:
                continue
            # List all the values in parsed_log
            for value in list(parsed_log.values()):
                if type(value) != str or value == '':
                    continue
                is_invalid, invalid_field_path = invalid_input_message(value, input_delta)
                if is_invalid:
                    return InvalidInputResult(invalid_field_path)
            # We reported error if we found error in the operator log
            # But it turned out the result was too fragile
            # So we disable it by default
            if actoConfig.alarms.warning_in_operator_logs:
                return ErrorResult(Oracle.ERROR_LOG, line)
        return PassResult()
