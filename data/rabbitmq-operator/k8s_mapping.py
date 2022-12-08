from known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'affinity'], AffinitySchema),
    K8sField(['spec', 'override', 'service'], ServiceSchema),
    K8sField(['spec', 'override', 'statefulSet'], StatefulSetSchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
    K8sField(['spec', 'persistence', 'storageClassName'], StorageClassNameSchema),
    K8sField(['spec', 'replicas'], ReplicasSchema),
    K8sField(['spec', 'service', 'type'], ServiceTypeSchema),
]

BLACKBOX = [
    K8sField(['spec', 'affinity'], AffinitySchema),
    K8sField(['spec', 'override', 'service'], ServiceSchema),
    K8sField(['spec', 'override', 'statefulSet'], StatefulSetSchema),
    K8sField(['spec', 'resources'], ResourceRequirementsSchema),
    K8sField(['spec', 'tolerations'], TolerationsSchema),
]