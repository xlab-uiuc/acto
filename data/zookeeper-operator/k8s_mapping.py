import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'image', 'pullPolicy'], known_schemas.ImagePullPolicySchema),
    known_schemas.K8sField(['spec', 'persistence', 'spec'], known_schemas.PersistentVolumeClaimSpecSchema),
    known_schemas.K8sField(['spec', 'containers', 'ITEM'], known_schemas.ContainerSchema),
    known_schemas.K8sField(['spec', 'initContainers', 'ITEM'], known_schemas.ContainerSchema),
    known_schemas.K8sField(['spec', 'pod', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'pod', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'pod', 'securityContext'], known_schemas.PodSecurityContextSchema),
    known_schemas.K8sField(['spec', 'pod', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'replicas'], known_schemas.ReplicasSchema),
    known_schemas.K8sField(['spec', 'volumes', 'ITEM'], known_schemas.VolumeSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'containers', 'ITEM'], known_schemas.ContainerSchema),
    known_schemas.K8sField(['spec', 'initContainers', 'ITEM'], known_schemas.ContainerSchema),
    known_schemas.K8sField(['spec', 'persistence', 'spec'], known_schemas.PersistentVolumeClaimSpecSchema),
    known_schemas.K8sField(['spec', 'pod', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'pod', 'resources'], known_schemas.ComputeResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'pod', 'securityContext'], known_schemas.PodSecurityContextSchema),
    known_schemas.K8sField(['spec', 'pod', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'pod', 'serviceAccountName'], known_schemas.ServiceAccountNameSchema),
    known_schemas.K8sField(['spec', 'volumes', 'ITEM'], known_schemas.VolumeSchema),
]