import json
import os
import re
import argparse

def count_config(path):
    file = os.path.join(path, "test_plan.json")
    with open (file, "r", encoding="utf-8") as f:
        config = json.load(f)["normal_testcases"]

    key = list(config.keys())[0]
    prop = set()
    for test in config[key]:
        prop.add(re.search(r".*_(\[.*\])_.*", test).group(1))

    print(prop)
    
    return len(prop)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, help="Path to the testrun folder")
    args = parser.parse_args()

    print(count_config(args.path))

    



