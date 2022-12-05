import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'override', 'service'], known_schemas.ServiceSchema),
    known_schemas.K8sField(['spec', 'override', 'statefulSet'], known_schemas.StatefulSetSchema),
    known_schemas.K8sField(['spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'persistence', 'storageClassName'], known_schemas.StorageClassNameSchema),
    known_schemas.K8sField(['spec', 'replicas'], known_schemas.ReplicasSchema),
    known_schemas.K8sField(['spec', 'service', 'type'], known_schemas.ServiceTypeSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'override', 'service'], known_schemas.ServiceSchema),
    known_schemas.K8sField(['spec', 'override', 'statefulSet'], known_schemas.StatefulSetSchema),
    known_schemas.K8sField(['spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'tolerations'], known_schemas.TolerationsSchema),
]