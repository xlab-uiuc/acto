import argparse
import yaml
import json

parser = argparse.ArgumentParser(description=
    "A helper for pruning input generation space. This tool will calculate the number of leaves under every path and print the top 10 levels.\n" +
    "For example: python3 prune_tool.py -p $[CRD path]\n"
)

parser.add_argument('--path',
                    '-p',
                    dest='path',
                    required=True,
                    help="CRD yaml file path")

args = parser.parse_args()

'''
[Example]
python3 prune_tool.py -p ../data/zookeeper-operator/crds/zookeeper.pravega.io_zookeeperclusters_crd.yaml

level 0
{
    "": 2131
}
.
.
.
level 9
{
    ".spec.versions.0.schema.openAPIV3Schema.properties.spec.properties.volumes": 559,
    ".spec.versions.0.schema.openAPIV3Schema.properties.spec.properties.containers": 453,
    ".spec.versions.0.schema.openAPIV3Schema.properties.spec.properties.initContainers": 453,
    ".spec.versions.0.schema.openAPIV3Schema.properties.spec.properties.pod": 358,
    ...
}

=> volumes / containers / initContainers / pod can be considered to prune. 
'''

with open(args.path) as file:
    crd_yaml = yaml.load(file, Loader=yaml.FullLoader)
    
    num_descendants_dict = {}
    def buildTree(d, path, level):
        num_descendants_dict[level] = num_descendants_dict.get(level, {})
        if type(d) is dict:
            for key in d.keys():
                num_descendants_dict[level][path] = num_descendants_dict[level].get(path, 0) + buildTree(d[key], path + "." + key, level + 1)
            return num_descendants_dict[level].get(path, 1) # It is possible for dictionary with zero child.
        elif type(d) is list:
            for i in range(len(d)):
                num_descendants_dict[level][path] = num_descendants_dict[level].get(path, 0) + buildTree(d[i], path + "." + str(i), level + 1)
            return num_descendants_dict[level].get(path, 1) 
        else:
            num_descendants_dict[level][path] = 1
            return 1
    buildTree(crd_yaml, "", 0)

    # Print top 10 levels
    max_depth = len(num_descendants_dict)
    for level in range(0, min(10, max_depth)):
        print("level " + str(level))
        sorted_dict = dict(sorted(num_descendants_dict[level].items(), key=lambda item: item[1], reverse=True))
        print(json.dumps(sorted_dict, indent=4))

    '''
    # Simple testcases

    'crds/zookeeper.pravega.io_zookeeperclusters_crd.yaml'
    assert(num_descendants_dict[1][".metadata"] == 1)
    assert(num_descendants_dict[2][".spec.names"] == 5)
    assert(num_descendants_dict[9]['.spec.versions.0.schema.openAPIV3Schema.properties.spec.properties.clientService'] == 5)
    assert(num_descendants_dict[9]['.spec.versions.0.schema.openAPIV3Schema.properties.spec.properties.adminServerService'] == 6) 
    '''    