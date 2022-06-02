import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'nodeSelector'], False),
    input.CopiedOverField(['spec', 'securityContext'], False),
    input.CopiedOverField(['spec', 'tolerations'], True),
    
    input.ProblemMaticField(['spec', 'redisFollower', 'affinity'], False),
    input.ProblemMaticField(['spec', 'redisLeader', 'affinity'], False),
    input.ProblemMaticField(['spec', 'storage', 'volumeClaimTemplate'], False),
]
