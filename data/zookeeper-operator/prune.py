import acto.input.input as input

custom_fields = [
    input.CopiedOverField(['spec', 'containers', 'ITEM']),
    input.CopiedOverField(['spec', 'initContainers', 'ITEM']),
    input.CopiedOverField(['spec', 'persistence', 'spec'], used_fields=[
        ['spec', 'persistence', 'annotations'],
        ['spec', 'persistence', 'spec', 'accessModes'],
        ['spec', 'persistence', 'spec', 'resources', 'requests']
    ]),
    input.CopiedOverField(['spec', 'pod', 'affinity']),
    input.CopiedOverField(['spec', 'pod', 'resources'], used_fields=[
        ['spec', 'pod', 'resources', 'limits'],
        ['spec', 'pod', 'resources', 'requests']
    ]),
    input.CopiedOverField(['spec', 'pod', 'securityContext']),
    input.CopiedOverField(['spec', 'pod', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'volumes', 'ITEM']),
    input.OverSpecifiedField(['spec', 'volumeMounts'], array=True),

    input.CopiedOverField(['spec', 'ephemeral', 'emptydirvolumesource']),
]