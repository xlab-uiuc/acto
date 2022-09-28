import sys

sys.path.append('../..')
import input


custom_fields = [
    input.CopiedOverField(['spec', 'affinity']),
    input.CopiedOverField(['spec', 'tolerations'], True),
    input.CopiedOverField(['spec', 'topologySpreadConstraints'], True),
    input.CopiedOverField(['spec', 'dataStore', 'pvc', 'spec']),
    input.CopiedOverField(['spec', 'dataStore', 'pvc', 'source']),
    input.CopiedOverField(['spec', 'dataStore', 'hostPath']),
]