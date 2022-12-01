import input
import sys

sys.path.append('../..')

custom_fields = [
    input.CopiedOverField(['spec', 'kubernetesConfig', 'resources']),
    input.CopiedOverField(['spec', 'nodeSelector']),

    input.CopiedOverField(['spec', 'redisExporter', 'resources']),
    input.CopiedOverField(['spec', 'redisFollower', 'affinity']),
    input.CopiedOverField(['spec', 'redisFollower', 'livenessProbe']),
    input.CopiedOverField(['spec', 'redisFollower', 'readinessProbe']),
    input.CopiedOverField(['spec', 'redisLeader', 'affinity']),
    input.CopiedOverField(['spec', 'redisLeader', 'livenessProbe']),
    input.CopiedOverField(['spec', 'redisLeader', 'readinessProbe']),

    input.CopiedOverField(['spec', 'securityContext']),
    input.CopiedOverField(['spec', 'sidecars', 'ITEM', 'resources']),
    input.CopiedOverField(['spec', 'resources']),
    input.CopiedOverField(['spec', 'storage', 'volumeClaimTemplate']),
    input.OverSpecifiedField(['spec', 'tolerations'], array=True),
]
