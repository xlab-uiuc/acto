from acto.input.known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'deployments', 'ITEM', 'affinity'], AffinitySchema),
    K8sField(['spec', 'deployments', 'ITEM', 'tolerations'], TolerationsSchema),
]

BLACKBOX = [
    K8sField(['spec', 'deployments', 'ITEM', 'affinity'], AffinitySchema),
    K8sField(['spec', 'deployments', 'ITEM', 'tolerations'], TolerationsSchema),
]