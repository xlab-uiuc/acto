import input

custom_fields = [
    input.CopiedOverField(['spec', 'containers', 'ITEM']),
    input.CopiedOverField(['spec', 'initContainers', 'ITEM']),
    input.CopiedOverField(['spec', 'ephemeral', 'emptydirvolumesource']),
    input.CopiedOverField(['spec', 'persistence', 'spec']),
    input.CopiedOverField(['spec', 'pod', 'affinity']),
    input.CopiedOverField(['spec', 'pod', 'resources']),
    input.CopiedOverField(['spec', 'pod', 'securityContext']),
    input.CopiedOverField(['spec', 'pod', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'volumes', 'ITEM']),
    input.CopiedOverField(['spec', 'volumeMounts'], array=True),
]