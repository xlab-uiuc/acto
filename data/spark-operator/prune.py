import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'volumes'], False),
    
    input.ProblemMaticField(['spec', 'timeToLiveSeconds'], "integer"),
]
