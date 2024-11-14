import os
import json
import yaml
import re

from acto.checker.impl.state_compare import CustomCompareMethods
from acto.common import flatten_dict

with open("test.txt") as f:
    lines = f.read().split("\n")
config_data = [x + "\n" for x in lines[15:]]
mark = 0
for i in range(len(config_data)):
    config_data[i] = re.sub("(\w+):", '"\g<1>":', config_data[i])
    config_data[i] = re.sub("'(.+)'", '"\g<1>"', config_data[i])
    if '\"ok\":' in config_data[i]:
        mark = i
        break
config_data[mark - 1] = re.sub("(\w*)},", '\g<1>}', config_data[mark - 1])
config_data = json.loads("".join(config_data[:mark] + ["}"]))["parsed"]

with open("system_state.json") as f:
    mongo_yaml = json.load(f)
cr = mongo_yaml["custom_resource_spec"]

if (
    "replsets" in cr
    and len(cr["replsets"]) > 0
    and "configuration" in cr["replsets"][0]
):
    mongo_yaml = yaml.load(cr["replsets"][0]["configuration"], Loader=yaml.FullLoader)
    

compare_methods = CustomCompareMethods()
print(compare_methods.equals(mongo_yaml, config_data))



