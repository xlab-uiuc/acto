import sys

sys.path.append('../..')
import input

custom_fields = [
    # input.CopiedOverField(['spec', 'initContainers']),
    input.CopiedOverField(['spec', 'persistence']),
    # input.CopiedOverField(['spec', 'containers']),
    # input.CopiedOverField(['spec', 'volumes']),
    input.CopiedOverField(['spec', 'pod']),
]