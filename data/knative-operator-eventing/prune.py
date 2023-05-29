import acto.input.input as input

custom_fields = [
    input.OverSpecifiedField(['spec', 'deployments', 'INDEX', 'tolerations'], array=True),
    input.OverSpecifiedField(['spec', 'deployments', 'INDEX', 'affinity']),
    
    input.ProblematicField(['spec', 'registry', 'override']),
]
