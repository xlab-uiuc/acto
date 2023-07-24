import logging
from dataclasses import dataclass
from typing import List, Optional

from acto.checker.checker import BinaryChecker, OracleResult, OracleControlFlow, means_first
from acto.common import invalid_input_message
from acto.config import actoConfig
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger

"""
This checker is used to check the output of kubectl cli command.
If kubectl reject the mutation, an error result will be returned.
"""


@dataclass
class KubectlCliResult(OracleResult):
    invalid_field_path: Optional[List[str]] = None

    @means_first(lambda self: not self.means_terminate())
    def means_ok(self):
        return self.message == OracleControlFlow.ok or self.message == "Custom resource remain unchanged"

    @means_first(lambda self: not self.means_terminate())
    def means_revert(self):
        return self.message.startswith('Invalid input, field path:')

    @means_first(lambda self: not self.means_terminate())
    def means_redo(self):
        return self.message.startswith('Connection refused, stderr: ')

    def means_terminate(self):
        return super().means_terminate() or self.message == 'Connection failed too many times. Abort'


class KubectlCliChecker(BinaryChecker):
    name = 'input'
    retry_timeout = 60
    max_retry = 2

    def _binary_check(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
        logger = get_thread_logger(with_prefix=True)

        stdout, stderr = snapshot.cli_result['stdout'], snapshot.cli_result['stderr']

        if "unchanged" in stdout or "unchanged" in stderr:
            logger.info('CR unchanged, continue')
            return KubectlCliResult(message='Custom resource remain unchanged')

        if stderr == '':
            logger.info('No stderr, continue')
            return KubectlCliResult()

        if 'connection refused' in stderr or 'deadline exceeded' in stderr:
            logger.info('Connection refused, reject mutation')
            retry_count_key = f'{self.name}_retry'
            old_retry_count = snapshot.get_context_value(retry_count_key) or 0
            if old_retry_count >= self.max_retry:
                return KubectlCliResult('Connection failed too many times. Abort')
            snapshot.set_context_value(retry_count_key, old_retry_count + 1)
            return KubectlCliResult('Connection refused, stderr: ' + stderr, time_to_wait_until_next_step=self.retry_timeout)

        input_delta, _ = snapshot.delta(prev_snapshot)
        is_invalid, invalid_field_path = invalid_input_message(stderr, input_delta)

        if is_invalid:
            logger.info('Invalid input, reject mutation')
            logger.info('STDOUT: ' + stdout)
            logger.info('STDERR: ' + stderr)
            return KubectlCliResult(message=f'Invalid input, field path: {invalid_field_path}', invalid_field_path=invalid_field_path)

        logger.log(logging.CRITICAL if actoConfig.strict else logging.ERROR,
                   f'stderr is not empty, but invalid_input_message mark it as valid: {stderr}')
        return KubectlCliResult()
