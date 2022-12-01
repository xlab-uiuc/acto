import input
import sys

sys.path.append('../..')

custom_fields = [
    input.CopiedOverField(['spec', 'kubernetesConfig', 'resources']),
    input.CopiedOverField(['spec', 'nodeSelector'], False),
    input.CopiedOverField(['spec', 'securityContext'], False),
    input.CopiedOverField(['spec', 'tolerations'], True),

    input.CopiedOverField(['spec', 'redisExporter', 'resources']),
    input.CopiedOverField(['spec', 'redisFollower', 'affinity'], False),
    input.CopiedOverField(['spec', 'redisFollower', 'livenessProbe'], False),
    input.CopiedOverField(['spec', 'redisFollower', 'readinessProbe'], False),
    input.CopiedOverField(['spec', 'redisLeader', 'affinity'], False),
    input.CopiedOverField(['spec', 'redisLeader', 'livenessProbe'], False),
    input.CopiedOverField(['spec', 'redisLeader', 'readinessProbe'], False),
    input.CopiedOverField(['spec', 'sidecars', 'ITEM', 'resources']),
    input.CopiedOverField(['spec', 'resources']),
    input.CopiedOverField(['spec', 'storage', 'volumeClaimTemplate'], False),
]
