import logging
from dataclasses import dataclass
from functools import cached_property
from typing import List, Optional

from acto.checker.checker import Checker, OracleResult
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

    @cached_property
    def means_flush(self):
        return self.message == 'Custom resource remain unchanged'

    @cached_property
    def means_revert(self):
        return self.message.startswith('Invalid input, field path:')

    @cached_property
    def means_terminate(self):
        return self.message.startswith('Connection refused, stderr: ')


class KubectlCliChecker(Checker):
    name = 'input'

    def _check(self, snapshot: Snapshot, prev_snapshot: Snapshot) -> OracleResult:
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
            return KubectlCliResult('Connection refused, stderr: ' + stderr)

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
