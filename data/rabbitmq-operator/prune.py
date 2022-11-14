import sys

sys.path.append('../..')
import input


custom_fields = [
    input.CopiedOverField(['spec', 'override', 'service']),
    input.OverSpecifiedField(['spec', 'override', 'statefulSet', 'spec']),
    input.CopiedOverField(['spec', 'affinity']),
    input.CopiedOverField(['spec', 'tolerations'], array=True)
]