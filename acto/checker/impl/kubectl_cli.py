import logging

from acto.checker.checker import Checker
from acto.common import OracleResult, PassResult, InvalidInputResult, UnchangedInputResult, ConnectionRefusedResult, invalid_input_message
from acto.config import actoConfig
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

        if "unchanged" in stdout or "unchanged" in stderr:
            logger.info('CR unchanged, continue')
            return UnchangedInputResult()

        if stderr == '':
            logger.info('No stderr, continue')
            return PassResult()

        if 'connection refused' in stderr or 'deadline exceeded' in stderr:
            logger.info('Connection refused, reject mutation')
            return ConnectionRefusedResult()

        input_delta, _ = snapshot.delta(prev_snapshot)
        is_invalid, invalid_field_path = invalid_input_message(stderr, input_delta)

        if is_invalid:
            logger.info('Invalid input, reject mutation')
            logger.info('STDOUT: ' + stdout)
            logger.info('STDERR: ' + stderr)
            return InvalidInputResult(invalid_field_path)

        logger.log(logging.CRITICAL if actoConfig.strict else logging.ERROR,
                   f'stderr is not empty, but invalid_input_message mark it as valid: {stderr}')
        return PassResult()
