import input
import sys

sys.path.append('../..')

custom_fields = [
    input.CopiedOverField(['spec', 'kubernetesConfig', 'resources']),
    input.CopiedOverField(['spec', 'redisExporter', 'resources']),
    input.CopiedOverField(['spec', 'redisFollower', 'affinity']),
    input.CopiedOverField(['spec', 'redisLeader', 'affinity']),
    input.CopiedOverField(['spec', 'resources']),
    input.CopiedOverField(['spec', 'securityContext']),
    input.CopiedOverField(['spec', 'sidecars', 'ITEM', 'resources']),
    input.CopiedOverField(['spec', 'storage', 'volumeClaimTemplate']),
    input.CopiedOverField(['spec', 'tolerations'], array=True),
]