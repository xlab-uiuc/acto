from acto.input.input import OverSpecifiedField

custom_fields = [
    OverSpecifiedField(["spec", "affinity"]),
    OverSpecifiedField(["spec", "containerSecurityContext"]),
    OverSpecifiedField(["spec", "envVars"], array=True),
    OverSpecifiedField(["spec", "initContainers"]),
    OverSpecifiedField(["spec", "livenessProbe"]),
    OverSpecifiedField(["spec", "readinessProbe"]),
    OverSpecifiedField(["spec", "securityContext"]),
    OverSpecifiedField(["spec", "tolerations"], array=True),
    OverSpecifiedField(["spec", "volumes"], array=True),
]
