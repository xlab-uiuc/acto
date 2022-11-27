import input

custom_fields = [
    input.OverSpecifiedField(['spec', 'deployments', 'INDEX', 'tolerations'], True),
    input.OverSpecifiedField(['spec', 'deployments', 'INDEX', 'affinity']),

    input.ProblematicField(['spec', 'ingress', 'istio']),
    input.ProblematicField(['spec', 'registry', 'override']),
]
