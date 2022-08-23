'''Parser that maps the KOData manifest to Knative Serving/Eventing CR
    Author: @essoz
    Date: 2022-08-22
'''

'''Override resources
Knative-Serving
1. configMap
3. services
4. deployments
5. podDisruptionBudgets


Knative-Eventing
1. configMap
2. services
3. deployments
4. podDisruptionBudgets
'''




import yaml
import argparse
import json
def get_kind(manifest: dict):
    return manifest['kind']


def get_name(manifest: dict):
    return manifest['metadata']['name']


def get_labels(manifest: dict):
    return manifest['metadata']['labels']


def get_annotations(manifest: dict):
    return manifest['metadata']['annotations']


def get_env(manifest: dict):
    if manifest['kind'] != 'Deployment':
        return None
    # get env from every container in the manifest
    env_entries = []
    for container in manifest['spec']['template']['spec']['containers']:
        env = {"container": container['name'],
               "envVars": container['env'] if 'env' in container else []}
        env_entries.append(env)
    if len(env_entries) > 0:
        return env_entries

    return None


def get_replicas(manifest: dict):
    if manifest['kind'] != 'Deployment' and manifest['kind'] != 'StatefulSet':
        return None
    if 'replicas' in manifest['spec']:
        if manifest['spec']['replicas'] > 0:
            return manifest['spec']['replicas']

    return None


def get_node_selector(manifest: dict):
    if manifest['kind'] != 'Deployment' and manifest['kind'] != 'StatefulSet':
        return None

        # if there is a node selector, return it
    if 'nodeSelector' in manifest['spec']['template']['spec']:
        return manifest['spec']['template']['spec']['nodeSelector']
    else:
        return None


def get_tolerations(manifest: dict):
    if manifest['kind'] != "Deployment":
        return None

    # if there is tolerations, return it
    if 'tolerations' in manifest['spec']['template']['spec']:
        return manifest['spec']['template']['spec']['tolerations']
    else:
        return None


def get_affinity(manifest: dict):
    if manifest['kind'] != "Deployment":
        return None

    # if there is an affinity, return it
    if 'affinity' in manifest['spec']['template']['spec']:
        return manifest['spec']['template']['spec']['affinity']
    else:
        return None


def get_resources(manifest: dict):
    if manifest['kind'] != "Deployment":
        return None

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
    if manifest['kind'] != "Service":
        return None

    if 'selector' in manifest['spec']:
        return manifest['spec']['selector']

    return None


def get_min_available(manifest: dict):
    if manifest['kind'] != 'PodDisruptionBudget':
        return None

    if 'minAvailable' in manifest['spec']:
        return manifest['spec']['minAvailable']

    return None
    # env override
    '''The env entries should be fetched from spec.template.conainers.name'''


def construct_override(manifests, funcs):
    if len(manifests) == 0:
        return None

    overrides = []
    for manifest in manifests:
        override = {}
        for field, func in funcs:
            value = func(manifest)
            if value != None:
                override[field] = value
        if len(override.keys()) > 0:
            overrides.append(override)

    return overrides


def construct_config_override(manifests, funcs):
    if len(manifests) == 0:
        return None

    overrides = {}

    for manifest in manifests:
        overrides[get_name(manifest)] = manifest['data']

    return overrides


funcs = [
    ('name', get_name),
    # ('labels', get_labels),
    # ('annotations', get_annotations),
    ('env', get_env),
    ('replicas', get_replicas),
    ('nodeSelector', get_node_selector),
    ('tolerations', get_tolerations),
    ('affinity', get_affinity),
    ('resources', get_resources),
    ('selector', get_selector),
    ('minAvailable', get_min_available),
]


def flatten_list(l: list, curr_path: list) -> list:
    '''Convert list into list of tuples (path, value)

    Args:
        l: list to be flattened
        curr_path: current path of d

    Returns:
        list of Tuples (path, basic value)
    '''
    result = []
    for idx, value in enumerate(l):
        path = curr_path + [idx]
        if isinstance(value, dict):
            result.extend(flatten_dict(value, path))
        elif isinstance(value, list):
            result.extend(flatten_list(value, path))
        else:
            result.append((path, value))
    return result


def flatten_dict(d: dict, curr_path: list) -> list:
    '''Convert dict into list of tuples (path, value)

    Args:
        d: dict to be flattened
        curr_path: current path of d

    Returns:
        list of Tuples (path, basic value)
    '''
    result = []
    for key, value in d.items():
        path = curr_path + [key]
        if isinstance(value, dict):
            result.extend(flatten_dict(value, path))
        elif isinstance(value, list):
            result.extend(flatten_list(value, path))
        else:
            result.append((path, value))
    return result


if __name__ == "__main__":
    # parse arguments here
    parser = argparse.ArgumentParser(
        description='Parse KOData manifest to Knative Serving/Eventing CR')

    parser.add_argument(
        '-i', '--input', help='input KOData manifest file', type=str,  required=True)
    parser.add_argument(
        '-s', '--seed', help='path to seed CR file, no output file will be generated if none', type=str, default=None)
    parser.add_argument(
        '-c', '--context', help='path to the context file, skipped if None', type=str, default=None
    )
    args = parser.parse_args()

    kind_of_interest = 'Deployment', "ConfigMap", "Service", "PodDisruptionBudget"

    manifests = {
        "Deployment": [],
        "ConfigMap": [],
        "Service": [],
        "PodDisruptionBudget": []
    }

    all_manifests = yaml.load_all(
        open('data/knative-operator-serving/kodata/2-serving-core.yaml', 'r'), Loader=yaml.FullLoader)

    for manifest in all_manifests:
        if manifest == None:
            continue
        if get_kind(manifest) in manifests:
            manifests[get_kind(manifest)].append(manifest)

    dp_override = construct_override(manifests['Deployment'], funcs)
    svc_override = construct_override(manifests['Service'], funcs)
    pdb_override = construct_override(manifests['PodDisruptionBudget'], funcs)
    config_override = construct_config_override(manifests['ConfigMap'], funcs)

    if args.seed != None:
        file_name = args.seed.split('/')[-1]
        file_name_without_suffix = file_name.split('.')[0]
        output_file_path = '/'.join(args.seed.split('/')
                                    [:-1]) + f'/{file_name_without_suffix}-override.yaml'

        cr = yaml.load(open(args.seed, 'r'), Loader=yaml.FullLoader)

        cr['spec']['config'] = config_override
        cr['spec']['deployments'] = dp_override
        cr['spec']['services'] = svc_override
        cr['spec']['podDisruptionBudgets'] = pdb_override
        with open(output_file_path, 'w') as f:
            yaml.dump(cr, f)

    if args.context != None:
        # load context in json format
        context = json.load(open(args.context, 'r'))

        # sanity check
        if 'analysis_result' not in context:
            context['analysis_result'] = {}

        if 'default_value_map' not in context['analysis_result']:
            context['analysis_result']['default_value_map'] = {}

        # construct default value map
        flattened_overrides = []
        flattened_overrides += flatten_list(dp_override,
                                            ["root", "spec", "deployments"]) \
            + flatten_list(svc_override, ["root", "spec", "services"]) \
            + flatten_list(pdb_override, ["root", "spec", "podDisruptionBudgets"]) \
            + flatten_dict(config_override, ["root", "spec", "config"])

        # convert flattened_overrides to a dict according to key value pairs
        for key, value in flattened_overrides:
            context['analysis_result']['default_value_map'][str(key)] = value

        # pretty dump context to json file
        with open(args.context, 'w') as f:
            json.dump(context, f, indent=4)
