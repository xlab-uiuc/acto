import sys

sys.path.append('../..')
import input

custom_fields = [
    input.CopiedOverField(['spec', 'affinity']),
    input.OverSpecifiedField(['spec', 'discovery', 'additionalContainers'], array=True),
    input.OverSpecifiedField(['spec', 'discovery', 'additionalVolumes'], array=True),
    input.OverSpecifiedField(['spec', 'discovery', 'initContainers'], array=True),
    input.CopiedOverField(['spec', 'discovery', 'affinity']),
    input.CopiedOverField(['spec', 'discovery', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'discovery', 'podSecurityContext']),

    input.OverSpecifiedField(['spec', 'pd', 'additionalContainers'], array=True),
    input.OverSpecifiedField(['spec', 'pd', 'additionalVolumes'], array=True),
    input.CopiedOverField(['spec', 'pd', 'affinity']),
    input.OverSpecifiedField(['spec', 'pd', 'initContainers'], array=True),
    input.CopiedOverField(['spec', 'pd', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'pd', 'podSecurityContext']),

    input.CopiedOverField(['spec', 'podSecurityContext']),
    input.OverSpecifiedField(['spec', 'pump', 'additionalContainers'], array=True),
    input.CopiedOverField(['spec', 'pump', 'additionalVolumes'], array=True),
    input.CopiedOverField(['spec', 'pump', 'affinity']),
    input.CopiedOverField(['spec', 'pump', 'initContainers'], array=True),
    input.CopiedOverField(['spec', 'pump', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'pump', 'podSecurityContext']),

    input.OverSpecifiedField(['spec', 'ticdc', 'additionalContainers'], array=True),
    input.OverSpecifiedField(['spec', 'ticdc', 'additionalVolumes'], array=True),
    input.CopiedOverField(['spec', 'ticdc', 'affinity']),
    input.CopiedOverField(['spec', 'ticdc', 'initContainers'], array=True),
    input.CopiedOverField(['spec', 'ticdc', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'ticdc', 'podSecurityContext']), 

    input.OverSpecifiedField(['spec', 'tidb', 'additionalContainers'], array=True),
    input.OverSpecifiedField(['spec', 'tidb', 'additionalVolumes'], array=True),
    input.CopiedOverField(['spec', 'tidb', 'affinity']),
    input.OverSpecifiedField(['spec', 'tidb', 'initContainers'], array=True),
    input.CopiedOverField(['spec', 'tidb', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'tidb', 'podSecurityContext']),

    input.OverSpecifiedField(['spec', 'tiflash', 'additionalContainers'], array=True),
    input.OverSpecifiedField(['spec', 'tiflash', 'additionalVolumes'], array=True),
    input.CopiedOverField(['spec', 'tiflash', 'affinity']),
    input.CopiedOverField(['spec', 'tiflash', 'initContainers'], array=True),
    input.CopiedOverField(['spec', 'tiflash', 'initializer']),
    input.CopiedOverField(['spec', 'tiflash', 'logTailer'], used_fields=[
        ['spec', 'tiflash', 'logTailer', 'limits'],
        ['spec', 'tiflash', 'logTailer', 'requests'],
    ]),
    input.CopiedOverField(['spec', 'tiflash', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'tiflash', 'podSecurityContext']),

    input.OverSpecifiedField(['spec', 'tikv', 'additionalContainers'], array=True),
    input.OverSpecifiedField(['spec', 'tikv', 'additionalVolumes'], array=True),
    input.CopiedOverField(['spec', 'tikv', 'affinity']),
    input.OverSpecifiedField(['spec', 'tikv', 'initContainers'], array=True),
    input.CopiedOverField(['spec', 'tikv', 'logTailer'], used_fields=[
        ['spec', 'tikv', 'logTailer', 'limits'],
        ['spec', 'tikv', 'logTailer', 'requests'],
    ]),
    input.CopiedOverField(['spec', 'tikv', 'tolerations'], array=True),
    input.CopiedOverField(['spec', 'tikv', 'podSecurityContext']),
    input.CopiedOverField(['spec', 'tolerations'], array=True),

    input.ProblematicField(['spec', 'pd']),
    input.ProblematicField(['spec', 'tikv']),
    input.ProblematicField(['spec', 'tiflash']),
    input.ProblematicField(['spec', 'ticdc']),
    input.ProblematicField(['spec', 'pump']),
    input.ProblematicField(['spec', 'helper']),
    input.ProblematicField(['spec', 'paused']),
    input.ProblematicField(['spec', 'tlsCluster']),
]
