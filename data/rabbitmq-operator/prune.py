import sys

sys.path.append('../..')
import input


custom_fields = [
    input.CopiedOverField(['spec', 'override']),
    input.CopiedOverField(['spec', 'affinity']),
    input.CopiedOverField(['spec', 'tolerations'], array=True)
]