from acto.input.known_schemas import K8sField, TolerationsSchema
from acto.input.known_schemas.pod_schemas import (
    AffinitySchema,
    ContainersSchema,
    EnvVarSchema,
    LivenessProbeSchema,
    PodSecurityContextSchema,
    ReadinessProbeSchema,
    SecurityContextSchema,
    VolumeSchema,
)

BLACKBOX = [
    K8sField(["spec", "affinity"], AffinitySchema),
    K8sField(["spec", "containerSecurityContext"], SecurityContextSchema),
    K8sField(["spec", "envVars", "ITEM"], EnvVarSchema),
    K8sField(["spec", "initContainers"], ContainersSchema),
    K8sField(["spec", "livenessProbe"], LivenessProbeSchema),
    K8sField(["spec", "readinessProbe"], ReadinessProbeSchema),
    K8sField(["spec", "securityContext"], PodSecurityContextSchema),
    K8sField(["spec", "tolerations"], TolerationsSchema),
    K8sField(["spec", "volumes", "ITEM"], VolumeSchema),
]
