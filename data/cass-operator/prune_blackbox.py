import input

custom_fields = [
    input.CopiedOverField(['spec', 'configBuilderResources']),
    input.CopiedOverField(['spec', 'podTemplateSpec']),
    input.CopiedOverField(['spec', 'resources']),
    input.CopiedOverField(['spec', 'storageConfig', 'additionalVolumes', 'ITEM', 'pvcSpec']),
    input.CopiedOverField(['spec', 'storageConfig', 'cassandraDataVolumeClaimSpec']),
    input.CopiedOverField(['spec', 'systemLoggerResources']),
    input.CopiedOverField(['spec', 'tolerations'], array=True),
]