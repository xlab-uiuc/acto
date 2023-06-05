from acto.input.known_schemas import *

WHITEBOX = [
    K8sField(['spec', 'statefulSet', 'spec'], StatefulSetSpecSchema),
]

BLACKBOX = [
    K8sField(['spec', 'statefulSet', 'spec'], StatefulSetSpecSchema),
]