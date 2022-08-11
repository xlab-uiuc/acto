import yaml


def get_name(manifest: dict):
    return manifest['metadata']['name']


# no need to override the labels


def get_labels(manifest: dict):
    return manifest['metadata']['labels']


# no need to override the annotations


def get_annotations(manifest: dict):
    return manifest['metadata']['annotations']


def get_env(manifest: dict):
    # get env from every container in the manifest
    env_entries = []
    for container in manifest['spec']['template']['spec']['containers']:
        if not ('env' in container):
            continue

        env = {"container": container['name'], "envVars": container['env']}
        env_entries.append(env)
    if len(env_entries) > 0:
        return env_entries

    return None


def get_replicas(manifest: dict):
    if 'replicas' in manifest['spec']:
        if manifest['spec']['replicas'] > 0:
            return manifest['spec']['replicas']

    return None


def get_node_selector(manifest: dict):
    # if there is a node selector, return it
    if 'nodeSelector' in manifest['spec']['template']['spec']:
        return manifest['spec']['template']['spec']['nodeSelector']
    else:
        return None


def get_tolerations(manifest: dict):
    # if there is tolerations, return it
    if 'tolerations' in manifest['spec']['template']['spec']:
        return manifest['spec']['template']['spec']['tolerations']
    else:
        return None


def get_affinity(manifest: dict):
    # if there is an affinity, return it
    if 'affinity' in manifest['spec']['template']['spec']:
        return manifest['spec']['template']['spec']['affinity']
    else:
        return None


def get_resources(manifest: dict):
    # get resources from every container in the manifest
    resources_entries = []
    for container in manifest['spec']['template']['spec']['containers']:
        if not ('resources' in container):
            continue
        resources = {"container": container['name']}

        if 'limits' in container['resources']:
            resources['limits'] = container['resources']['limits']
        if 'requests' in container['resources']:
            resources['requests'] = container['resources']['requests']

        if len(resources.keys()) > 1:
            resources_entries.append(resources)

    if len(resources_entries) > 0:
        return resources_entries
    else:
        return None


def get_selector(manifest: dict):
    if 'selector' in manifest['spec']:
        return manifest['spec']['selector']

    return None


def get_min_available(manifest: dict):
    if 'minAvailable' in manifest['spec']:
        return manifest['spec']['minAvailable']

    return None
    # env override
    '''The env entries should be fetched from spec.template.conainers.name'''


if __name__ == "__main__":
    types = ['serving', 'eventing']

    for type in types:
        dps = yaml.load(open(f'data/knative-operator-{type}/dps.yaml'),
                        Loader=yaml.SafeLoader)['items']

        svcs = yaml.load(open(f'data/knative-operator-{type}/svcs.yaml'),
                         Loader=yaml.SafeLoader)['items']

        pdbs = yaml.load(open(f'data/knative-operator-{type}/pdbs.yaml'),
                         Loader=yaml.SafeLoader)['items']

        deployment_override_fields = [
            ('name', get_name),
            # ('labels', get_labels),
            # ('annotations', get_annotations),
            ('env', get_env),
            ('replicas', get_replicas),
            ('nodeSelector', get_node_selector),
            ('tolerations', get_tolerations),
            ('affinity', get_affinity),
            ('resources', get_resources),
        ]

        service_override_fields = [
            ('name', get_name),
            # ('labels', get_labels),
            # ('annotations', get_annotations),
            ('selector', get_selector),
        ]

        pod_disruption_budget_override_fields = [
            ('name', get_name),
            ('minAvailable', get_min_available),
        ]

        dps_override = []
        svcs_override = []
        pdbs_override = []

        for dp in dps:
            dp_override = {}
            for field, func in deployment_override_fields:
                override = func(dp)
                if override != None:
                    dp_override[field] = override
            if len(dp_override.keys()) > 0:
                dps_override.append(dp_override)

        for svc in svcs:
            svc_override = {}
            for field, func in service_override_fields:
                override = func(svc)
                if override != None:
                    svc_override[field] = override

            if len(svc_override.keys()) > 0:
                svcs_override.append(svc_override)

        for pdb in pdbs:
            pdb_override = {}
            for field, func in pod_disruption_budget_override_fields:
                override = func(pdb)
                if override != None:
                    pdb_override[field] = override
            if len(pdb_override.keys()) > 0:
                pdbs_override.append(pdb_override)

        cr = yaml.load(
            open(f'data/knative-operator-{type}/cr.yaml'), Loader=yaml.SafeLoader)
        if len(dps_override) > 0:
            cr['spec']['deployments'] = dps_override
        if len(svcs_override) > 0:
            cr['spec']['services'] = svcs_override
        if len(pdbs_override) > 0:
            cr['spec']['podDisruptionBudgets'] = pdbs_override

        with open(f'data/knative-operator-{type}/cr-override.yaml', 'w') as f:
            yaml.dump(cr, f)
