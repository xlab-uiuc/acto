import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'imagePullSecrets'], array=True),
    input.CopiedOverField(['spec', 'backup', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'backup', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'resources'], used_fields=[
        ['spec', 'replsets', 'ITEM', 'arbiter', 'resources', 'limits'],
    ]),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'sidecarPVCs'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'sidecarVolumes'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'sidecars'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'arbiter', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'livenessProbe']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'resources'], used_fields=[
        ['spec', 'replsets', 'ITEM', 'nonvoting', 'resources', 'limits'],
    ]),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'sidecarPVCs', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'sidecarVolumes', 'ITEM', 'ephemeral', 'volumeClaimTemplate']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'sidecars', 'ITEM']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'nonvoting', 'volumeSpec', 'persistentVolumeClaim']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'resources'], used_fields=[
        ['spec', 'replsets', 'ITEM', 'resources', 'limits'],
    ]),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'readinessProbe']),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'sidecarPVCs'], array=True),
    input.OverSpecifiedField(['spec', 'replsets', 'ITEM', 'sidecarVolumes'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'sidecars'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'replsets', 'ITEM', 'volumeSpec']),
    input.OverSpecifiedField(['spec', 'sharding', 'configsvrReplSet']), # append
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'livenessProbe']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'resources'], used_fields=[
        ['spec', 'sharding', 'mongos', 'resources', 'limits'],
    ]),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'readinessProbe']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'sidecarPVCs'], array=True),
    input.OverSpecifiedField(['spec', 'sharding', 'mongos', 'sidecarVolumes'], array=True),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'sidecars'], array=True),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'tolerations'], array=True),

    input.ProblematicField(['spec', 'pmm']),  # ignore external dependency
    input.ProblematicField(['spec', 'crVersion'], string=True),  # ignore external dependency
    input.ProblematicField(['spec', 'mongod', 'setParameter']),  # ignore external dependency
    input.ProblematicField(['spec', 'mongod', 'security']),
    input.ProblematicField(['spec', 'mongod', 'replication']),
    input.ProblematicField(['spec', 'mongod', 'operationProfiling']),
]