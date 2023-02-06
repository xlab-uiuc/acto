import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'redis', 'affinity']),
    input.CopiedOverField(['spec', 'redis', 'exporter', 'args'], array=True),
    input.CopiedOverField(['spec', 'redis', 'exporter', 'resources']),
    input.CopiedOverField(['spec', 'redis', 'resources']),
    input.CopiedOverField(['spec', 'redis', 'securityContext']),
    input.CopiedOverField(['spec', 'redis', 'storage', 'persistentVolumeClaim', 'spec']),
    input.CopiedOverField(['spec', 'redis', 'storage', 'persistentVolumeClaim', 'metadata', 'annotations']),
    input.CopiedOverField(['spec', 'redis', 'storage', 'persistentVolumeClaim', 'metadata', 'labels']),
    input.CopiedOverField(['spec', 'redis', 'storage', 'persistentVolumeClaim', 'status']),
    input.CopiedOverField(['spec', 'redis', 'storage', 'emptyDir']),
    input.CopiedOverField(['spec', 'redis', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'sentinel', 'affinity']),
    input.CopiedOverField(['spec', 'sentinel', 'exporter', 'args'], array=True),
    input.CopiedOverField(['spec', 'sentinel', 'exporter', 'resources']),
    input.CopiedOverField(['spec', 'sentinel', 'resources']),
    input.CopiedOverField(['spec', 'sentinel', 'securityContext']),
    input.CopiedOverField(['spec', 'sentinel', 'tolerations'], array=True),
]
