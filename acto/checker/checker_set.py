"""Oracle checker set of Acto."""

from typing import Optional

from acto.checker.impl.consistency import ConsistencyChecker
from acto.checker.impl.crash import CrashChecker
from acto.checker.impl.health import HealthChecker
from acto.checker.impl.operator_log import OperatorLogChecker
from acto.common import flatten_dict
from acto.input.input import InputModel
from acto.oracle_handle import OracleHandle
from acto.result import OracleResults
from acto.snapshot import Snapshot
from acto.utils import get_thread_logger


class CheckerSet:
    """CheckerSet is a set of checkers that are run on each generation."""

    def __init__(
        self,
        context: dict,
        trial_dir: str,
        input_model: InputModel,
        oracle_handle: OracleHandle,
        checker_generators: Optional[list] = None,
    ):
        if checker_generators:
            checker_generators.extend(checker_generators)
        self.context = context
        self.input_model = input_model
        self.trial_dir = trial_dir

        self._crash_checker = CrashChecker()
        self._health_checker = HealthChecker()
        self._operator_log_checker = OperatorLogChecker()
        self._consistency_checker = ConsistencyChecker(
            trial_dir=self.trial_dir,
            context=self.context,
            input_model=self.input_model,
        )
        _ = oracle_handle

    def check(
        self,
        snapshot: Snapshot,
        prev_snapshot: Snapshot,
        generation: int,
    ) -> OracleResults:
        """Run all checkers on the given snapshot and return the result."""
        logger = get_thread_logger(with_prefix=True)

        if snapshot.system_state == {}:
            logger.warning("System state is empty, skipping check")
            return OracleResults()

        input_delta, system_delta = snapshot.delta(prev_snapshot)
        flattened_system_state = flatten_dict(snapshot.system_state, [])

        if len(input_delta) > 0:
            num_delta = 0
            for resource_delta_list in system_delta.values():
                for type_delta_list in resource_delta_list.values():
                    num_delta += len(type_delta_list)
            logger.info(
                "Number of system state fields: [%d] Number of delta: [%d]",
                len(flattened_system_state),
                num_delta,
            )

        # generation_result_path = os.path.join(
        #     self.trial_dir, f"generation-{generation:03d}-runtime.json"
        # )
        # with open(generation_result_path, "w", encoding="utf-8") as f:
        #     json.dump(run_result.to_dict(), f, cls=ActoEncoder, indent=4)

        return OracleResults(
            crash=self._crash_checker.check(
                generation, snapshot, prev_snapshot
            ),
            health=self._health_checker.check(
                generation, snapshot, prev_snapshot
            ),
            operator_log=self._operator_log_checker.check(
                generation, snapshot, prev_snapshot
            ),
            consistency=self._consistency_checker.check(
                generation, snapshot, prev_snapshot
            ),
        )

    def count_num_fields(self, snapshot: Snapshot, prev_snapshot: Snapshot):
        """Count the number of fields in the system state and the number of delta."""
        input_delta, system_delta = snapshot.delta(prev_snapshot)
        flattened_system_state = flatten_dict(snapshot.system_state, [])

        if len(input_delta) > 0:
            num_delta = 0
            for resource_delta_list in system_delta.values():
                for type_delta_list in resource_delta_list.values():
                    for _ in type_delta_list.values():
                        num_delta += 1
            return len(flattened_system_state), num_delta

        return None
