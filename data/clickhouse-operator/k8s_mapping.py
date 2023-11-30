from acto.input.known_schemas import (ImageSchema, K8sField, PodTemplateSchema,
                                      ResourceRequirementsSchema,
                                      TolerationsSchema)
from acto.input.known_schemas.resource_schemas import \
    ComputeResourceRequirementsSchema

WHITEBOX = [
    K8sField(['spec', 'serverImage'], ImageSchema),
]

BLACKBOX = [
    K8sField(['spec', 'configBuilderResources'], ResourceRequirementsSchema),
    K8sField(['spec', 'podTemplateSpec'], PodTemplateSchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'systemLoggerResources'], ComputeResourceRequirementsSchema),
    K8sField(['spec', 'configBuilderResources'], ComputeResourceRequirementsSchema),
    K8sField(['spec', 'storageConfig', 'additionalVolumes', 'ITEM', 'pvcSpec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'storageConfig', 'cassandraDataVolumeClaimSpec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'systemLoggerResources'], ResourceRequirementsSchema),
    K8sField(['spec', 'systemLoggerImage'], ImageSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
]