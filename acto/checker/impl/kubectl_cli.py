from acto.checker.checker import Checker
from acto.common import OracleResult, PassResult, InvalidInputResult, UnchangedInputResult, ConnectionRefusedResult, invalid_input_message
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger

"""
This checker is used to check the output of kubectl cli command.
If kubectl reject the mutation, an error result will be returned.
"""


class KubectlCliChecker(Checker):
    name = 'input'

    def check(self, _: int, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        logger = get_thread_logger(with_prefix=True)

        stdout, stderr = snapshot.cli_result['stdout'], snapshot.cli_result['stderr']

        if stderr.find('connection refused') != -1 or stderr.find('deadline exceeded') != -1:
            logger.info('Connection refused, reject mutation')
            return ConnectionRefusedResult()

        input_delta, _ = snapshot.delta(prev_snapshot)
        is_invalid, invalid_field_path = invalid_input_message(stderr, input_delta)

        # the stderr should indicate the invalid input
        if len(stderr) > 0:
            is_invalid = True

        if is_invalid:
            logger.info('Invalid input, reject mutation')
            logger.info('STDOUT: ' + stdout)
            logger.info('STDERR: ' + stderr)
            return InvalidInputResult(invalid_field_path)

        if stdout.find('unchanged') != -1 or stderr.find('unchanged') != -1:
            logger.info('CR unchanged, continue')
            return UnchangedInputResult()

        return PassResult()
