import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'deployments', 'ITEM', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'deployments', 'ITEM', 'tolerations'], known_schemas.TolerationsSchema),
    known_schemas.K8sField(['spec', 'ingress', 'kourier', 'service-type'], known_schemas.ServiceTypeSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'deployments', 'ITEM', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'deployments', 'ITEM', 'tolerations'], known_schemas.TolerationsSchema),
]