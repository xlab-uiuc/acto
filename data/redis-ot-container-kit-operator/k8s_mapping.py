import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'kubernetesConfig', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redisExporter', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redisFollower', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'redisLeader', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'securityContext'], known_schemas.PodSecurityContextSchema),
    known_schemas.K8sField(['spec', 'sidecars', 'ITEM', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'storage', 'volumeClaimTemplate', 'spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'tolerations'], known_schemas.TolerationsSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'kubernetesConfig', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redisExporter', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'redisFollower', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'redisLeader', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'securityContext'], known_schemas.PodSecurityContextSchema),
    known_schemas.K8sField(['spec', 'sidecars', 'ITEM', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'storage', 'volumeClaimTemplate', 'spec', 'resources'], known_schemas.ResourceRequirementsSchema),
    known_schemas.K8sField(['spec', 'tolerations'], known_schemas.TolerationsSchema),
]