import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'redis', 'affinity']),
    input.CopiedOverField(['spec', 'redis', 'tolerations']),
    input.CopiedOverField(['spec', 'redis', 'storage', 'persistentVolumeClaim']),
    input.CopiedOverField(['spec', 'redis', 'storage', 'emptyDir']),
    input.CopiedOverField(['spec', 'redis', 'resources']),
    input.CopiedOverField(['spec', 'redis', 'securityContext']),
    input.CopiedOverField(['spec', 'redis', 'exporter', 'args'], True),
    input.CopiedOverField(['spec', 'redis', 'exporter', 'resources']),
    input.CopiedOverField(['spec', 'sentinel', 'affinity']),
    input.CopiedOverField(['spec', 'sentinel', 'tolerations']),
    input.CopiedOverField(['spec', 'sentinel', 'securityContext']),
    input.CopiedOverField(['spec', 'sentinel', 'exporter', 'args'], True),
    input.CopiedOverField(['spec', 'sentinel', 'exporter', 'resources']),
]
