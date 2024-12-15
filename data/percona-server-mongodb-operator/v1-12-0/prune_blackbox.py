import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'backup', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'backup', 'resources']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'resources']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'sidecarPVCs', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'sidecarVolumes', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'sidecars', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'tolerations'], array=True),

    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'containerSecurityContext']),

    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'resources']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'readinessProbe']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'livenessProbe']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'sidecarPVCs', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'sidecarVolumes', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'sidecars', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'volumeSpec', 'persistentVolumeClaim']),

    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'resources']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'readinessProbe']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'sidecarPVCs', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'sidecarVolumes', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'sidecars', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'volumeSpec', 'persistentVolumeClaim']),

    input.CopiedOverField(['spec', 'sharding', 'configsvrReplSet']),

    input.CopiedOverField(['spec', 'sharding', 'mongos', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'resources']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'readinessProbe']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'livenessProbe']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'sidecarPVCs', 'ITEM']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'sidecarVolumes', 'ITEM']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'sidecars', 'ITEM']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'tolerations'], array=True),

    input.ProblematicField(['spec', 'pmm']),  # ignore external dependency
    input.ProblematicField(['spec', 'crVersion'], string=True),  # ignore external dependency
    input.ProblematicField(['spec', 'mongod', 'setParameter']),  # ignore external dependency
    input.ProblematicField(['spec', 'mongod', 'security']),
    input.ProblematicField(['spec', 'mongod', 'replication']),
    input.ProblematicField(['spec', 'mongod', 'operationProfiling']),
]