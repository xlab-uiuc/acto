import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'redis', 'affinity']),
    input.CopiedOverField(['spec', 'redis', 'tolerations']),
    input.CopiedOverField(['spec', 'redis', 'storage', 'persistentVolumeClaim']),
    input.CopiedOverField(['spec', 'sentinel', 'affinity']),
    input.CopiedOverField(['spec', 'sentinel', 'tolerations']),
]
