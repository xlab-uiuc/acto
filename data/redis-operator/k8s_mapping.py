import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'redis', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'redis', 'exporter', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redis', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redis', 'securityContext'], known_schemas.PodSecurityContextSchema),
    known_schemas.K8sField(['spec', 'redis', 'storage', 'persistentVolumeClaim', 'spec', 'resources'], known_schemas.StorageResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redis', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'redis', 'priorityClassName'], known_schemas.PriorityClassNameSchema),
    known_schemas.K8sField(['spec', 'redis', 'replicas'], known_schemas.ReplicasSchema),
    known_schemas.K8sField(['spec', 'redis', 'serviceAccountName'], known_schemas.ReplicasSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'sentinel', 'exporter', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'securityContext'], known_schemas.PodSecurityContextSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'priorityClassName'], known_schemas.PriorityClassNameSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'replicas'], known_schemas.ReplicasSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'serviceAccountName'], known_schemas.ReplicasSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'redis', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'redis', 'exporter', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redis', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redis', 'securityContext'], known_schemas.PodSecurityContextSchema),
    known_schemas.K8sField(['spec', 'redis', 'storage', 'persistentVolumeClaim', 'spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redis', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'sentinel', 'exporter', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'securityContext'], known_schemas.PodSecurityContextSchema),
    known_schemas.K8sField(['spec', 'sentinel', 'tolerations'], known_schemas.TolerationsSchema),
]