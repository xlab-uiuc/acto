import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'volumes'], True),
    
    input.ProblemMaticField(['spec', 'timeToLiveSeconds'], "integer"),
]
