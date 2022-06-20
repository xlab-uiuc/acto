import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'haproxy', 'affinity']),
    input.CopiedOverField(['spec', 'haproxy', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'haproxy', 'livenessProbe']),
    input.CopiedOverField(['spec', 'haproxy', 'readinessProbe']),
    input.CopiedOverField(['spec', 'haproxy', 'tolerations']),
    input.CopiedOverField(['spec', 'haproxy', 'sidecars'], True),
    input.CopiedOverField(['spec', 'haproxy', 'sidecarsVolumes'], True),
    input.CopiedOverField(['spec', 'haproxy', 'sidecarsPVCs'], True),
    input.CopiedOverField(['spec', 'haproxy', 'volumeSpec']),

    input.CopiedOverField(['spec', 'proxysql', 'affinity']),
    input.CopiedOverField(['spec', 'proxysql', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'proxysql', 'livenessProbe']),
    input.CopiedOverField(['spec', 'proxysql', 'readinessProbe']),
    input.CopiedOverField(['spec', 'proxysql', 'tolerations']),
    input.CopiedOverField(['spec', 'proxysql', 'sidecars'], True),
    input.CopiedOverField(['spec', 'proxysql', 'sidecarsVolumes'], True),
    input.CopiedOverField(['spec', 'proxysql', 'sidecarsPVCs'], True),
    input.CopiedOverField(['spec', 'proxysql', 'volumeSpec']),

    input.CopiedOverField(['spec', 'pxc', 'affinity']),
    input.CopiedOverField(['spec', 'pxc', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'pxc', 'livenessProbe']),
    input.CopiedOverField(['spec', 'pxc', 'readinessProbe']),
    input.CopiedOverField(['spec', 'pxc', 'tolerations']),
    input.CopiedOverField(['spec', 'pxc', 'sidecars'], True),
    input.CopiedOverField(['spec', 'pxc', 'sidecarsVolumes'], True),
    input.CopiedOverField(['spec', 'pxc', 'sidecarsPVCs'], True),
    input.CopiedOverField(['spec', 'pxc', 'volumeSpec']),
]