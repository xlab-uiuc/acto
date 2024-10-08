"""Crawls yaml examples from target repo as testing material"""

import argparse
import glob
import os

import yaml

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Crawl CR examples in the project repo"
    )
    parser.add_argument(
        "--dir", dest="dir", help="Project repo dir", required=True
    )
    parser.add_argument(
        "--kind", "-k", dest="kind", help="CR kind", required=False
    )
    # parser.add_argument('--dest',
    #                     dest='dest',
    #                     help='Directory to store the crawlled examples',
    #                     required=True)

    args = parser.parse_args()

    main_results = []
    aux_results = []

    for file in glob.glob(
        os.path.join(args.dir, "**", "*.yaml"), recursive=True
    ):
        with open(file, "r", encoding="utf-8") as yaml_file:
            try:
                file_content = yaml.load(yaml_file, Loader=yaml.FullLoader)
            except yaml.YAMLError as e:
                continue
            if "kind" in file_content:
                try:
                    if file_content["namespace"] != "":
                        file_content.pop("namespace", None)
                except KeyError as e:
                    print("No namespace, no op")

                try:
                    if file_content["metadata"]["namespace"] != "":
                        file_content["metadata"].pop("namespace", None)
                except KeyError as e:
                    print("No metadata.namespace, no op")

                try:
                    if file_content["spec"]["datacenter"]["namespace"] != "":
                        file_content["spec"]["datacenter"].pop(
                            "namespace", None
                        )
                except KeyError as e:
                    print("No spec.datacenter.namespace, no op")

                if file_content["kind"] == "Deployment":
                    continue
                elif file_content["kind"] == args.kind:
                    print(file)
                    main_results.append(file_content)
                elif file_content["kind"] == "StorageClass":
                    print(file)
                    file_content["provisioner"] = "rancher.io/local-path"
                    aux_results.append(file_content)
                elif file_content["kind"] != "CustomResourceDefinition":
                    print(file)
                    aux_results.append(file_content)

    with open("examples.yaml", "w", encoding="utf-8") as out_file:
        yaml.dump_all(main_results, out_file)
    with open("aux-examples.yaml", "w", encoding="utf-8") as out_file:
        yaml.dump_all(aux_results, out_file)
