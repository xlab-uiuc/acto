import sys

sys.path.append('../..')
import input


custom_fields = [
    input.CopiedOverField(['spec', 'affinity']),
    input.CopiedOverField(['spec', 'resources']),
    input.CopiedOverField(['spec', 'tolerations'], True),
    input.CopiedOverField(['spec', 'topologySpreadConstraints'], True),
    input.CopiedOverField(['spec', 'dataStore', 'pvc', 'spec']),
    input.CopiedOverField(['spec', 'dataStore', 'pvc', 'source']),
    input.CopiedOverField(['spec', 'dataStore', 'hostPath']),
    input.CopiedOverField(['spec', 'nodeSelector']),
    
    input.OverSpecifiedField(['spec', 'ingress', 'sql', 'tls']),
    input.OverSpecifiedField(['spec', 'ingress', 'ui', 'tls', 'INDEX', 'hosts']),
]