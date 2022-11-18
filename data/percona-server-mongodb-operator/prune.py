import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'imagePullSecrets']),
    input.CopiedOverField(['spec', 'backup', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'backup', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'affinity']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'livenessProbe']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'nonvoting']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'readinessProbe']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'sidecarPVCs'], True),
    input.OverSpecifiedField(['spec', 'replsets', 'items', 'sidecarVolumes'], True),
    input.CopiedOverField(['spec', 'replsets', 'items', 'sidecars'], True),
    input.CopiedOverField(['spec', 'replsets', 'items', 'tolerations'], True),
    input.CopiedOverField(['spec', 'replsets', 'items', 'volumeSpec']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'arbiter', 'affinity']),
    input.CopiedOverField(['spec', 'replsets', 'items', 'arbiter', 'sidecarPVCs'], True),
    input.CopiedOverField(['spec', 'replsets', 'items', 'arbiter', 'sidecarVolumes'], True),
    input.CopiedOverField(['spec', 'replsets', 'items', 'arbiter', 'sidecars'], True),
    input.CopiedOverField(['spec', 'replsets', 'items', 'arbiter', 'tolerations'], True),
    input.CopiedOverField(['spec', 'replsets', 'items', 'nonvoting', 'volumeSpec', 'persistentVolumeClaim']),
    input.OverSpecifiedField(['spec', 'sharding', 'configsvrReplSet']), # append
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'affinity', 'advanced']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'containerSecurityContext']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'livenessProbe']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'readinessProbe']),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'sidecarPVCs'], True),
    input.OverSpecifiedField(['spec', 'sharding', 'mongos', 'sidecarVolumes'], True),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'sidecars'], True),
    input.CopiedOverField(['spec', 'sharding', 'mongos', 'tolerations'], True),

    input.ProblematicField(['spec', 'pmm']),  # ignore external dependency
    input.ProblematicField(['spec', 'crVersion']),  # ignore external dependency
    input.ProblematicField(['spec', 'mongod', 'setParameter']),  # ignore external dependency
    input.ProblematicField(['spec', 'mongod', 'security']),
    input.ProblematicField(['spec', 'mongod', 'replication']),
    input.ProblematicField(['spec', 'mongod', 'operationProfiling']),
]