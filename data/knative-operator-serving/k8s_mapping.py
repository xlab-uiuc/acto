from acto.input.known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'deployments', 'ITEM', 'affinity'], AffinitySchema),
    K8sField(['spec', 'deployments', 'ITEM', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'ingress', 'kourier', 'service-type'], ServiceTypeSchema),
]

BLACKBOX = [
    K8sField(['spec', 'deployments', 'ITEM', 'affinity'], AffinitySchema),
    K8sField(['spec', 'deployments', 'ITEM', 'tolerations'], TolerationsSchema),
]