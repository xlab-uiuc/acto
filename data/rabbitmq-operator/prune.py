import acto.input.input as input

custom_fields = [
    input.OverSpecifiedField(['spec', 'override', 'service']),
    input.OverSpecifiedField(['spec', 'override', 'statefulSet', 'spec']),
    input.OverSpecifiedField(['spec', 'override', 'statefulSet', 'spec', 'volumeClaimTemplates'], array=True),
    input.OverSpecifiedField(['spec', 'override', 'statefulSet', 'spec', 'updateStrategy']),
    input.OverSpecifiedField(['spec', 'override', 'statefulSet', 'spec', 'template']),
    input.OverSpecifiedField(['spec', 'override', 'service', 'spec']),
    input.CopiedOverField(['spec', 'affinity']),
    input.CopiedOverField(['spec', 'tolerations'], array=True),
    input.PatchField(['spec', 'override', 'statefulSet', 'spec'])
]