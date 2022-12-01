import sys

sys.path.append('../..')
import input


custom_fields = [
    input.CopiedOverField(['spec', 'affinity']),
    input.CopiedOverField(['spec', 'dataStore', 'pvc', 'spec']),
    input.CopiedOverField(['spec', 'resources']),
    input.CopiedOverField(['spec', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'topologySpreadConstraints'], True),
]