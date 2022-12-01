import input

custom_fields = [
    input.CopiedOverField(['spec', 'deployments', 'INDEX', 'tolerations'], True),
    input.CopiedOverField(['spec', 'deployments', 'INDEX', 'affinity']),
    
    input.ProblematicField(['spec', 'registry', 'override']),
]
