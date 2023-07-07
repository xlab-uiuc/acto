import yaml
from deepdiff.helper import NotPresent

from acto.common import Diff
from acto.snapshot import Snapshot


def test_delta():
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
    snapshot_prev = Snapshot(yaml.safe_load(input_prev), {}, {}, [])
    snapshot_curr = Snapshot(yaml.safe_load(input_curr), {}, {}, [])
    input_delta, _ = snapshot_curr.delta(snapshot_prev)
    assert input_delta == {'dictionary_item_added': {"root['spec']['override'][statefulSet][spec]": Diff(prev=NotPresent(), curr={}, path=['spec', 'override', 'statefulSet', 'spec'])}}
