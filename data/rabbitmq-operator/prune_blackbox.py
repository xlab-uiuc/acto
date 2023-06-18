import sys

sys.path.append('../..')
import input


custom_fields = [
    input.CopiedOverField(['spec', 'affinity']),
    input.CopiedOverField(['spec', 'override', 'service']),
    input.CopiedOverField(['spec', 'override', 'statefulSet']),
    input.CopiedOverField(['spec', 'resources']),
    input.CopiedOverField(['spec', 'tolerations'], array=True),
    input.PatchField(['spec', 'override', 'statefulSet', 'spec'])
]