"""Test snapshot."""
import yaml
from deepdiff.helper import NotPresent

from acto.common import Diff, PropertyPath
from acto.snapshot import Snapshot


def test_delta():
    """This test tests the delta function of Snapshot class."""
    input_prev = """
spec:
  image: null
"""
    input_curr = """
spec:
  image: null
  override:
    statefulSet:
      spec: {}
    """
    snapshot_prev = Snapshot(
        input_cr=yaml.safe_load(input_prev),
        cli_result={},
        system_state={},
        operator_log=[],
        events={},
        not_ready_pods_logs=None,
        generation=0,
    )
    snapshot_curr = Snapshot(
        input_cr=yaml.safe_load(input_curr),
        cli_result={},
        system_state={},
        operator_log=[],
        events={},
        not_ready_pods_logs=None,
        generation=0,
    )
    input_delta, _ = snapshot_curr.delta(snapshot_prev)
    print(input_delta)
    assert input_delta == {
        "dictionary_item_added": {
            "root['spec']['override'][statefulSet][spec]": Diff(
                prev=NotPresent(),
                curr={},
                path=PropertyPath(["spec", "override", "statefulSet", "spec"]),
            )
        }
    }
