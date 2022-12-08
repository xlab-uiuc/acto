from known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'affinity'], AffinitySchema),
    K8sField(['spec', 'dataStore', 'pvc', 'spec', 'resources'], StorageResourceRequirementsSchema),
    K8sField(['spec', 'resources'], ComputeResourceRequirementsSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'topologySpreadConstraints'], TopologySpreadConstraintsSchema),
]

BLACKBOX = [
    K8sField(['spec', 'affinity'], AffinitySchema),
    K8sField(['spec', 'dataStore', 'pvc', 'spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'topologySpreadConstraints'], TopologySpreadConstraintsSchema),
]