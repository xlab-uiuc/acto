import known_schemas

WHITEBOX = [
    known_schemas.K8sField(['spec', 'statefulSet', 'spec'], known_schemas.StatefulSetSpecSchema),
]

BLACKBOX = [
    known_schemas.K8sField(['spec', 'statefulSet', 'spec'], known_schemas.StatefulSetSpecSchema),
]