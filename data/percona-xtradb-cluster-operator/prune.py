import input

custom_fields = [
    input.CopiedOverField(['spec', 'haproxy', 'affinity']),
    input.CopiedOverField(['spec', 'haproxy', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'haproxy', 'livenessProbes']),
    input.CopiedOverField(['spec', 'haproxy', 'readinessProbes']),
    input.CopiedOverField(['spec', 'haproxy', 'tolerations'], True),
    input.CopiedOverField(['spec', 'haproxy', 'sidecars'], True),
    input.CopiedOverField(['spec', 'haproxy', 'sidecarVolumes'], True),
    input.CopiedOverField(['spec', 'haproxy', 'sidecarPVCs'], True),
    input.CopiedOverField(['spec', 'haproxy', 'volumeSpec']),

    input.CopiedOverField(['spec', 'proxysql', 'affinity']),
    input.CopiedOverField(['spec', 'proxysql', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'proxysql', 'livenessProbes']),
    input.CopiedOverField(['spec', 'proxysql', 'readinessProbes']),
    input.CopiedOverField(['spec', 'proxysql', 'tolerations'], True),
    input.CopiedOverField(['spec', 'proxysql', 'sidecars'], True),
    input.CopiedOverField(['spec', 'proxysql', 'sidecarVolumes'], True),
    input.CopiedOverField(['spec', 'proxysql', 'sidecarPVCs'], True),
    input.CopiedOverField(['spec', 'proxysql', 'volumeSpec']),

    input.CopiedOverField(['spec', 'pxc', 'affinity']),
    input.CopiedOverField(['spec', 'pxc', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'pxc', 'livenessProbes']),
    input.CopiedOverField(['spec', 'pxc', 'readinessProbes']),
    input.CopiedOverField(['spec', 'pxc', 'tolerations'], True),
    input.CopiedOverField(['spec', 'pxc', 'sidecars'], True),
    input.CopiedOverField(['spec', 'pxc', 'sidecarVolumes'], True),
    input.CopiedOverField(['spec', 'pxc', 'sidecarPVCs'], True),
    input.CopiedOverField(['spec', 'pxc', 'volumeSpec']),
]