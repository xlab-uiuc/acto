import sys

sys.path.append('../..')
import input


custom_fields = [
    input.CopiedOverField(['spec', 'affinity']),
    input.OverSpecifiedField(['spec', 'dataStore', 'pvc', 'spec'], used_fields=[
        ['spec', 'dataStore', 'pvc', 'spec', 'resources', 'requests']
    ]),
    input.CopiedOverField(['spec', 'dataStore', 'pvc', 'source']),
    input.CopiedOverField(['spec', 'dataStore', 'hostPath']),
    input.CopiedOverField(['spec', 'resources']),
    input.CopiedOverField(['spec', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'topologySpreadConstraints'], array=True),
]