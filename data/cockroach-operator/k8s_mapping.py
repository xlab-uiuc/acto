from known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'nodes'], ReplicasSchema),
    K8sField(['spec', 'image', 'pullPolicy'], ImagePullPolicySchema),
    K8sField(['spec', 'grpcPort'], PortSchema),
    K8sField(['spec', 'httpPort'], PortSchema),
    K8sField(['spec', 'sqlPort'], PortSchema),
    K8sField(['spec', 'additionalArgs'], ArgsSchema),
    K8sField(['spec', 'resources'], ComputeResourceRequirementsSchema),
    K8sField(['spec', 'dataStore', 'pvc', 'spec'], PersistentVolumeClaimSpecSchema),
    K8sField(['spec', 'dataStore', 'hostPath'], HostPathVolumeSourceSchema),
    K8sField(['spec', 'affinity'], AffinitySchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'topologySpreadConstraints'], TopologySpreadConstraintsSchema),
]

BLACKBOX = [
    K8sField(['spec', 'affinity'], AffinitySchema),
    K8sField(['spec', 'dataStore', 'pvc', 'spec'], PersistentVolumeClaimSpecSchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'topologySpreadConstraints'], TopologySpreadConstraintsSchema),
]