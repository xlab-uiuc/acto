from known_schemas import K8sField, ResourceRequirementsSchema, PodTemplateSchema, TolerationsSchema
from known_schemas import ServiceAccountNameSchema, ImageSchema

WHITEBOX = [
    K8sField(['spec', 'configBuilderResources'], ResourceRequirementsSchema),
    K8sField(['spec', 'podTemplateSpec'], PodTemplateSchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'storageConfig', 'additionalVolumes', 'ITEM', 'pvcSpec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'storageConfig', 'cassandraDataVolumeClaimSpec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'systemLoggerResources'], ResourceRequirementsSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
]

BLACKBOX = [
    K8sField(['spec', 'configBuilderResources'], ResourceRequirementsSchema),
    K8sField(['spec', 'podTemplateSpec'], PodTemplateSchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'serviceAccount'], ServiceAccountNameSchema),
    K8sField(['spec', 'storageConfig', 'additionalVolumes', 'ITEM', 'pvcSpec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'storageConfig', 'cassandraDataVolumeClaimSpec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'systemLoggerResources'], ResourceRequirementsSchema),
    K8sField(['spec', 'systemLoggerImage'], ImageSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
]