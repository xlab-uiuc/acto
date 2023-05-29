from acto.input.known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'redis', 'affinity'], AffinitySchema),
    K8sField(['spec', 'redis', 'exporter', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redis', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redis', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'redis', 'storage', 'persistentVolumeClaim', 'spec', 'resources'], StorageResourceRequirementsSchema),
    K8sField(['spec', 'redis', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'redis', 'priorityClassName'], PriorityClassNameSchema),
    K8sField(['spec', 'redis', 'replicas'], ReplicasSchema),
    K8sField(['spec', 'redis', 'serviceAccountName'], ReplicasSchema),
    K8sField(['spec', 'sentinel', 'affinity'], AffinitySchema),
    K8sField(['spec', 'sentinel', 'exporter', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'sentinel', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'sentinel', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'sentinel', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'sentinel', 'priorityClassName'], PriorityClassNameSchema),
    K8sField(['spec', 'sentinel', 'replicas'], ReplicasSchema),
]

BLACKBOX = [
    K8sField(['spec', 'redis', 'affinity'], AffinitySchema),
    K8sField(['spec', 'redis', 'exporter', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redis', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redis', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'redis', 'storage', 'persistentVolumeClaim', 'spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'redis', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'sentinel', 'affinity'], AffinitySchema),
    K8sField(['spec', 'sentinel', 'exporter', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'sentinel', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'sentinel', 'securityContext'], PodSecurityContextSchema),
    K8sField(['spec', 'sentinel', 'tolerations'], TolerationsSchema),
]