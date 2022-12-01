import input
import schema

custom_fields = [
    input.CopiedOverField(['spec', 'configBuilderResources', 'limits']),
    input.CopiedOverField(['spec', 'configBuilderResources', 'requests']),
    input.OverSpecifiedField(['spec', 'podTemplateSpec', 'metadata'], used_fields=[
        ['spec', 'podTemplateSpec', 'metadata', 'annotations'],
        ['spec', 'podTemplateSpec', 'metadata', 'labels'],
    ]),
    input.OverSpecifiedField(['spec', 'podTemplateSpec', 'spec'], used_fields=[
        ['spec', 'podTemplateSpec', 'spec', 'volumes', 'ITEM'],
        ['spec', 'podTemplateSpec', 'spec', 'containers', 'ITEM'],
        ['spec', 'podTemplateSpec', 'spec', 'initContainers', 'ITEM'],
        ['spec', 'podTemplateSpec', 'spec', 'affinity'],
        ['spec', 'podTemplateSpec', 'spec', 'tolerations'],
        ['spec', 'podTemplateSpec', 'spec', 'nodeSelector'],
        ['spec', 'podTemplateSpec', 'spec', 'securityContext'],
        ['spec', 'podTemplateSpec', 'spec', 'priorityClassName'],
    ]),
    input.CopiedOverField(['spec', 'resources'], used_fields=[
        ['spec', 'resources', 'limits'],
        ['spec', 'resources', 'requests'],
    ]),
    input.CopiedOverField(['spec', 'storageConfig', 'additionalVolumes', 'ITEM', 'pvcSpec']),
    input.CopiedOverField(['spec', 'storageConfig', 'cassandraDataVolumeClaimSpec']),
    input.CopiedOverField(['spec', 'systemLoggerResources'], used_fields=[
        ['spec', 'systemLoggerResources', 'limits'],
        ['spec', 'systemLoggerResources', 'requests'],
    ]),
    input.OverSpecifiedField(['spec', 'managementApiAuth', 'manual']),
    input.CopiedOverField(['spec', 'tolerations'], array=True),
]