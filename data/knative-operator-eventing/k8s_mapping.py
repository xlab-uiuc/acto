import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'deployments', 'ITEM', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'deployments', 'ITEM', 'tolerations'], known_schemas.TolerationSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'deployments', 'ITEM', 'affinity'], known_schemas.AffinitySchema),
    known_schemas.K8sField(['spec', 'deployments', 'ITEM', 'tolerations'], known_schemas.TolerationSchema),
]