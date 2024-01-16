import json
import os
from typing import Optional, Tuple

import deepdiff
import pydantic
import yaml
from typing_extensions import Self

from acto.common import EXCLUDE_PATH_REGEX, Diff, postprocess_diff
from acto.serialization import ActoEncoder


def input_cr_path(trial_dir: str, generation: int) -> str:
    """Return the path of the input CR"""
    return f"{trial_dir}/mutated-{generation:03d}.yaml"


def system_state_path(trial_dir: str, generation: int) -> str:
    """Return the path of the system state"""
    return f"{trial_dir}/system-state-{generation:03d}.json"


def cli_output_path(trial_dir: str, generation: int) -> str:
    """Return the path of the cli output"""
    return f"{trial_dir}/cli-output-{generation:03d}.log"


def events_log_path(trial_dir: str, generation: int) -> str:
    """Return the path of the events log"""
    return f"{trial_dir}/events-{generation:03d}.json"


def not_ready_pods_log_path(trial_dir: str, generation: int) -> str:
    """Return the path of the events log"""
    return f"{trial_dir}/not-ready-pods-{generation:03d}.json"


def operator_log_path(trial_dir: str, generation: int) -> str:
    """Return the path of the operator log"""
    return f"{trial_dir}/operator-{generation:03d}.log"


class Snapshot(pydantic.BaseModel):
    """A Snapshot is a snapshot of the system state at a point of time.
    It contains the input_cr, CLI result of the kubectl, operator log, 
    system state containing all Kubernetes resources"""

    input_cr: dict = pydantic.Field(
        description="Input CR of the trial in python dict format"
    )
    cli_result: dict = pydantic.Field(
        description="CLI result of the kubectl command"
    )
    system_state: dict = pydantic.Field(
        description="System state of the cluster, including all Kubernetes resources"
    )
    operator_log: list[str]
    events: dict = pydantic.Field(description="Serialized Kubernetes V1EventList object")
    not_ready_pods_logs: Optional[dict] = pydantic.Field(
        description="Logs from unready pods", default=None
    )
    generation: int

    def delta(
        self, prev: Self
    ) -> Tuple[
        dict[str, dict[str, Diff]], dict[str, dict[str, dict[str, Diff]]]
    ]:
        """Return the delta between this snapshot and the previous snapshot"""
        input_delta = postprocess_diff(
            deepdiff.DeepDiff(prev.input_cr, self.input_cr, view="tree")
        )

        system_state_delta = {}
        for (
            resource_name,
            resource,
        ) in self.system_state.items():  # pylint: disable=no-member
            if resource_name not in prev.system_state:
                prev.system_state[resource_name] = {}
            system_state_delta[resource_name] = postprocess_diff(
                deepdiff.DeepDiff(
                    prev.system_state[resource_name],
                    resource,
                    exclude_regex_paths=EXCLUDE_PATH_REGEX,
                    view="tree",
                )
            )

        return input_delta, system_state_delta

    def dump(self, trial_dir: str):
        """Dump the snapshot to files"""
        # Dump CLI output
        with open(
            cli_output_path(trial_dir, self.generation), "w", encoding="utf-8"
        ) as fout:
            json.dump(self.cli_result, fout, cls=ActoEncoder, indent=4)

        # Dump Kubernetes events
        with open(
            events_log_path(trial_dir, self.generation), "w", encoding="utf-8"
        ) as fout:
            json.dump(self.events, fout, cls=ActoEncoder, indent=4)

        if self.not_ready_pods_logs is not None:
            with open(
                not_ready_pods_log_path(trial_dir, self.generation),
                "w",
                encoding="utf-8",
            ) as fout:
                json.dump(
                    self.not_ready_pods_logs, fout, cls=ActoEncoder, indent=4
                )

        with open(
            operator_log_path(trial_dir, self.generation), "w", encoding="utf-8"
        ) as fout:
            fout.write("\n".join(self.operator_log))

        # Dump system state
        with open(
            system_state_path(trial_dir, self.generation), "w", encoding="utf-8"
        ) as fout:
            json.dump(self.system_state, fout, cls=ActoEncoder, indent=4)

    @classmethod
    def load(cls, trial_dir: str, generation: int) -> Self:
        """Load a snapshot from files"""
        with open(
            cli_output_path(trial_dir, generation), "r", encoding="utf-8"
        ) as fin:
            cli_result = json.load(fin)

        with open(
            events_log_path(trial_dir, generation), "r", encoding="utf-8"
        ) as fin:
            events = json.load(fin)

        if os.path.exists(not_ready_pods_log_path(trial_dir, generation)):
            with open(
                not_ready_pods_log_path(trial_dir, generation),
                "r",
                encoding="utf-8",
            ) as fin:
                not_ready_pods_logs = json.load(fin)
        else:
            not_ready_pods_logs = None

        with open(
            operator_log_path(trial_dir, generation), "r", encoding="utf-8"
        ) as fin:
            operator_log = fin.read().splitlines()

        with open(
            system_state_path(trial_dir, generation), "r", encoding="utf-8"
        ) as fin:
            system_state = json.load(fin)

        with open(
            input_cr_path(trial_dir, generation),
            "r",
            encoding="utf-8",
        ) as fin:
            input_cr = yaml.safe_load(fin)

        return cls(
            input_cr=input_cr,
            cli_result=cli_result,
            system_state=system_state,
            operator_log=operator_log,
            events=events,
            not_ready_pods_logs=not_ready_pods_logs,
            generation=generation,
        )
