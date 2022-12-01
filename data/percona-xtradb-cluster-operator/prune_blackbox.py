import input

custom_fields = [
    input.ProblematicField(['spec', 'pmm']),
    input.ProblematicField(['spec', 'backup']),

    input.CopiedOverField(['spec', 'haproxy', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'haproxy', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'haproxy', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'haproxy', 'resources']),
    input.CopiedOverField(['spec', 'haproxy', 'sidecarPVCs', 'ITEM']),
    input.CopiedOverField(['spec', 'haproxy', 'sidecarResources']),
    input.CopiedOverField(['spec', 'haproxy', 'sidecarVolumes', 'ITEM']),
    input.CopiedOverField(['spec', 'haproxy', 'sidecars', 'ITEM']),
    input.CopiedOverField(['spec', 'haproxy', 'tolerations']),
    input.CopiedOverField(['spec', 'haproxy', 'volumeSpec', 'persistentVolumeClaim']),

    input.CopiedOverField(['spec', 'logcollector', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'logcollector', 'resources']),

    input.CopiedOverField(['spec', 'proxysql', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'proxysql', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'proxysql', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'proxysql', 'resources']),
    input.CopiedOverField(['spec', 'proxysql', 'sidecarPVCs', 'ITEM']),
    input.CopiedOverField(['spec', 'proxysql', 'sidecarResources']),
    input.CopiedOverField(['spec', 'proxysql', 'sidecarVolumes', 'ITEM']),
    input.CopiedOverField(['spec', 'proxysql', 'sidecars', 'ITEM']),
    input.CopiedOverField(['spec', 'proxysql', 'tolerations']),
    input.CopiedOverField(['spec', 'proxysql', 'volumeSpec', 'persistentVolumeClaim']),
    
    input.CopiedOverField(['spec', 'pxc', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'pxc', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'pxc', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'pxc', 'resources']),
    input.CopiedOverField(['spec', 'pxc', 'sidecarPVCs', 'ITEM']),
    input.CopiedOverField(['spec', 'pxc', 'sidecarResources']),
    input.CopiedOverField(['spec', 'pxc', 'sidecarVolumes', 'ITEM']),
    input.CopiedOverField(['spec', 'pxc', 'sidecars', 'ITEM']),
    input.CopiedOverField(['spec', 'pxc', 'tolerations']),
    input.CopiedOverField(['spec', 'pxc', 'volumeSpec', 'persistentVolumeClaim']),
]