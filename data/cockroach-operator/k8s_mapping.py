import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'dataStore', 'pvc', 'spec', 'resources'], known_schemas.StorageResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'resources'], known_schemas.ComputeResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'topologySpreadConstraints'], known_schemas.TopologySpreadConstraintsSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'dataStore', 'pvc', 'spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'topologySpreadConstraints'], known_schemas.TopologySpreadConstraintsSchema),
]