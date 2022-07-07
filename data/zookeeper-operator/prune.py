import input

custom_fields = [
    input.CopiedOverField(['spec', 'initContainers'], True),
    input.CopiedOverField(['spec', 'persistence']),
    input.CopiedOverField(['spec', 'containers'], True),
    input.CopiedOverField(['spec', 'volumes'], True),
    input.CopiedOverField(['spec', 'pod']),
]