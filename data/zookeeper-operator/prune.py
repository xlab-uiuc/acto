import input

custom_fields = [
    input.CopiedOverField(['spec', 'pod', 'imagePullSecrets'], True),
    input.CopiedOverField(['spec', 'pod', 'securityContext']),
    input.CopiedOverField(['spec', 'pod', 'tolerations'], True),
    input.CopiedOverField(['spec', 'pod', 'affinity']),
    input.CopiedOverField(['spec', 'pod', 'resources']),
    input.CopiedOverField(['spec', 'ephemeral', 'emptydirvolumesource']),
    input.CopiedOverField(['spec', 'initContainers'], True),
    input.CopiedOverField(['spec', 'persistence', 'spec']),
    input.CopiedOverField(['spec', 'containers'], True),
    input.CopiedOverField(['spec', 'volumes'], True),
]