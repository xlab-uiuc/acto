from known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'image', 'pullPolicy'], ImagePullPolicySchema),
    K8sField(['spec', 'ephemeral', 'emptydirvolumesource'], EmptyDirVolumeSourceSchema),
    K8sField(['spec', 'persistence', 'spec'], PersistentVolumeClaimSpecSchema),
    K8sField(['spec', 'containers', 'ITEM'], ContainerSchema),
    K8sField(['spec', 'initContainers', 'ITEM'], ContainerSchema),
    K8sField(['spec', 'pod', 'affinity'], AffinitySchema),
    K8sField(['spec', 'pod', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'pod', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'pod', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'pod', 'serviceAccountName'], ServiceAccountNameSchema),
    K8sField(['spec', 'replicas'], ReplicasSchema),
    K8sField(['spec', 'volumes', 'ITEM'], VolumeSchema),
    K8sField(['spec', 'ports', 'ITEM'], PortSchema),
    K8sField(['spec', 'probes', 'readinessProbe'], ReadinessProbeSchema),
    K8sField(['spec', 'probes', 'livenessProbe'], LivenessProbeSchema),
]

BLACKBOX = [
    K8sField(['spec', 'containers', 'ITEM'], ContainerSchema),
    K8sField(['spec', 'ephemeral', 'emptydirvolumesource'], EmptyDirVolumeSourceSchema),
    K8sField(['spec', 'initContainers', 'ITEM'], ContainerSchema),
    K8sField(['spec', 'persistence', 'spec'], PersistentVolumeClaimSpecSchema),
    K8sField(['spec', 'pod', 'affinity'], AffinitySchema),
    K8sField(['spec', 'pod', 'resources'], ComputeResourceRequirementsSchema),
    K8sField(['spec', 'pod', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'pod', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'pod', 'serviceAccountName'], ServiceAccountNameSchema),
    K8sField(['spec', 'volumes', 'ITEM'], VolumeSchema),
    K8sField(['spec', 'ports', 'ITEM'], PortSchema),
    K8sField(['spec', 'probes', 'readinessProbe'], ReadinessProbeSchema),
    K8sField(['spec', 'probes', 'livenessProbe'], LivenessProbeSchema),
]