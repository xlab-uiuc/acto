from acto.input.known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'kubernetesConfig', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'kubernetesConfig', 'imagePullPolicy'], ImagePullPolicySchema),
    K8sField(['spec', 'redisExporter', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redisExporter', 'imagePullPolicy'], ImagePullPolicySchema),
    K8sField(['spec', 'redisExporter', 'resources'], ComputeResourceRequirementsSchema),
    K8sField(['spec', 'redisFollower', 'readinessProbe'], ReadinessProbeSchema),
    K8sField(['spec', 'redisFollower', 'livenessProbe'], LivenessProbeSchema),
    K8sField(['spec', 'redisFollower', 'affinity'], AffinitySchema),
    K8sField(['spec', 'redisLeader', 'readinessProbe'], ReadinessProbeSchema),
    K8sField(['spec', 'redisLeader', 'livenessProbe'], LivenessProbeSchema),
    K8sField(['spec', 'redisLeader', 'affinity'], AffinitySchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'priorityClassName'], PriorityClassNameSchema),
    K8sField(['spec', 'sidecars', 'ITEM', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'storage', 'volumeClaimTemplate'], PersistentVolumeClaimSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
]

BLACKBOX = [
    K8sField(['spec', 'kubernetesConfig', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redisExporter', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redisExporter', 'imagePullPolicy'], ImagePullPolicySchema),
    K8sField(['spec', 'redisExporter', 'resources'], ComputeResourceRequirementsSchema),
    K8sField(['spec', 'redisFollower', 'readinessProbe'], ReadinessProbeSchema),
    K8sField(['spec', 'redisFollower', 'livenessProbe'], LivenessProbeSchema),
    K8sField(['spec', 'redisFollower', 'affinity'], AffinitySchema),
    K8sField(['spec', 'redisLeader', 'affinity'], AffinitySchema),
    K8sField(['spec', 'redisLeader', 'readinessProbe'], ReadinessProbeSchema),
    K8sField(['spec', 'redisLeader', 'livenessProbe'], LivenessProbeSchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'sidecars', 'ITEM', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'storage', 'volumeClaimTemplate'], PersistentVolumeClaimSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
]