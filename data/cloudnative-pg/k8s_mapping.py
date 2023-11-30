from acto.input.known_schemas import K8sField
from acto.input.known_schemas.pod_schemas import AffinitySchema, TopologySpreadConstraintsSchema
from acto.input.known_schemas.storage_schemas import PersistentVolumeClaimSpecSchema

BLACKBOX = [
    K8sField(['spec', 'affinity'], AffinitySchema),
    K8sField(['spec', 'storage', 'pvcTemplate'], PersistentVolumeClaimSpecSchema),
    K8sField(['spec', 'walStorage', 'pvcTemplate'], PersistentVolumeClaimSpecSchema),
    K8sField(['spec', 'topologySpreadConstraints'], TopologySpreadConstraintsSchema),
]
