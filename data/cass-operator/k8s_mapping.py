import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'configBuilderResources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'podTemplateSpec'], known_schemas.PodTemplateSchema),
    known_schemas.K8sField(['spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'storageConfig', 'additionalVolumes', 'ITEM', 'pvcSpec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'storageConfig', 'cassandraDataVolumeClaimSpec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'systemLoggerResources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'tolerations'], known_schemas.TolerationsSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'configBuilderResources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'podTemplateSpec'], known_schemas.PodTemplateSchema),
    known_schemas.K8sField(['spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'serviceAccount'], known_schemas.ServiceAccountNameSchema),
    known_schemas.K8sField(['spec', 'storageConfig', 'additionalVolumes', 'ITEM', 'pvcSpec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'storageConfig', 'cassandraDataVolumeClaimSpec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'systemLoggerResources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'systemLoggerImage'], known_schemas.ImageSchema),
    known_schemas.K8sField(['spec', 'tolerations'], known_schemas.TolerationsSchema),
]