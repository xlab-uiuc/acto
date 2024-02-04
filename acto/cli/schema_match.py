import argparse
import sys

import pandas as pd
from ruamel.yaml import YAML

from acto.input.k8s_schemas import K8sSchemaMatcher
from acto.schema.schema import extract_schema


def main():
    """Main function"""

    parser = argparse.ArgumentParser(
        description="Analyze the CRD file and output an annotated yaml file"
    )
    parser.add_argument(
        "--crd",
        required=True,
        help="Path to the yaml CRD file",
    )
    parser.add_argument(
        "--k8s-version",
        required=False,
        default="1.29",
        help="Kubernetes version to match the schema with",
    )
    parser.add_argument(
        "--output",
        required=False,
        help="Path to dump the system state to",
    )
    args = parser.parse_args()

    # read the CRD file
    yaml = YAML()
    with open(args.crd, "r", encoding="utf-8") as f:
        crd = yaml.load(f)

    # extract the schema
    schema_yaml = crd["spec"]["versions"][-1]["schema"]["openAPIV3Schema"]
    root = extract_schema([], schema_yaml)

    # match the schema with Kubernetes resource schemas
    schema_matcher = K8sSchemaMatcher.from_version(args.k8s_version)
    matches = schema_matcher.find_matched_schemas(root)

    # output the breakdown of the matched schema information
    df = pd.DataFrame(
        [
            {
                "k8s_schema_name": k8s_schema.k8s_schema_name,
                "schema_path": "/".join(schema.path),
            }
            for schema, k8s_schema in matches
        ]
    )

    print(df["k8s_schema_name"].value_counts().to_string())
    print(f"{len(matches)} schemas matched in total")

    # annotate the yaml file with the matched schema information
    for schema, k8s_schema in matches:
        comment = k8s_schema.k8s_schema_name
        curr = schema_yaml
        for segment in schema.path[:-1]:
            if segment == "ITEM":
                curr = curr["items"]
            else:
                curr = curr["properties"][segment]
        if schema.path[-1] != "ITEM":
            curr["properties"].yaml_add_eol_comment(comment, schema.path[-1])
        else:
            curr.yaml_add_eol_comment(comment, "items")

    # output the annotated yaml file
    if args.output is None:
        yaml.dump(crd, sys.stdout)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            yaml.dump(crd, f)
        print("Annotated CRD file dumped to", args.output)


if __name__ == "__main__":
    main()
