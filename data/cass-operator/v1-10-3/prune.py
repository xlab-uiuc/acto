from acto.input.input import CopiedOverField, OverSpecifiedField

custom_fields = [
    CopiedOverField(['spec', 'configBuilderResources', 'limits']),
    CopiedOverField(['spec', 'configBuilderResources', 'requests']),
    OverSpecifiedField(['spec', 'podTemplateSpec', 'metadata'], used_fields=[
        ['spec', 'podTemplateSpec', 'metadata', 'annotations'],
        ['spec', 'podTemplateSpec', 'metadata', 'labels'],
    ]),
    OverSpecifiedField(['spec', 'podTemplateSpec', 'spec'], used_fields=[
        ['spec', 'podTemplateSpec', 'spec', 'volumes', 'ITEM'],
        ['spec', 'podTemplateSpec', 'spec', 'containers', 'ITEM'],
        ['spec', 'podTemplateSpec', 'spec', 'initContainers', 'ITEM'],
        ['spec', 'podTemplateSpec', 'spec', 'affinity'],
        ['spec', 'podTemplateSpec', 'spec', 'tolerations'],
        ['spec', 'podTemplateSpec', 'spec', 'nodeSelector'],
        ['spec', 'podTemplateSpec', 'spec', 'securityContext'],
        ['spec', 'podTemplateSpec', 'spec', 'priorityClassName'],
    ]),
    CopiedOverField(['spec', 'resources'], used_fields=[
        ['spec', 'resources', 'limits'],
        ['spec', 'resources', 'requests'],
    ]),
    CopiedOverField(['spec', 'storageConfig', 'additionalVolumes', 'ITEM', 'pvcSpec']),
    CopiedOverField(['spec', 'storageConfig', 'cassandraDataVolumeClaimSpec']),
    CopiedOverField(['spec', 'systemLoggerResources'], used_fields=[
        ['spec', 'systemLoggerResources', 'limits'],
        ['spec', 'systemLoggerResources', 'requests'],
    ]),
    OverSpecifiedField(['spec', 'managementApiAuth', 'manual']),
    CopiedOverField(['spec', 'tolerations'], array=True),
]