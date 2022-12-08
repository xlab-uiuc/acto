from known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'kubernetesConfig', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redisExporter', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redisFollower', 'affinity'], AffinitySchema),
    K8sField(['spec', 'redisLeader', 'affinity'], AffinitySchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'sidecars', 'ITEM', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'storage', 'volumeClaimTemplate', 'spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
]

BLACKBOX = [
    K8sField(['spec', 'kubernetesConfig', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redisExporter', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redisFollower', 'affinity'], AffinitySchema),
    K8sField(['spec', 'redisLeader', 'affinity'], AffinitySchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'sidecars', 'ITEM', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'storage', 'volumeClaimTemplate', 'spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
]