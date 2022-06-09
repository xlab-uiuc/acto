import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'nodeSelector'], False),
    input.CopiedOverField(['spec', 'securityContext'], False),
    input.CopiedOverField(['spec', 'tolerations'], True),
    
    input.ProblemMaticField(['spec', 'redisFollower', 'affinity'], "object"),
    input.ProblemMaticField(['spec', 'redisLeader', 'affinity'], "object"),
    input.ProblemMaticField(['spec', 'storage', 'volumeClaimTemplate'], "object"),
]
