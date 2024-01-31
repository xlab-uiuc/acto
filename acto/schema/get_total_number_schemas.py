import argparse
import logging
import sys

import yaml

from .schema import extract_schema


def get_total_number_schemas(raw_schema: dict) -> int:
    """Get the total number of schema nodes in a raw schema"""
    root = extract_schema([], raw_schema)
    base, over_specified, copied_over = root.get_all_schemas()
    return len(base) + len(over_specified) + len(copied_over)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Counts the total number of schema nodes in a CRD"
    )
    parser.add_argument(
        "--crd-file", help="Path to the CRD file", type=str, required=True
    )
    parser.add_argument(
        "--crd-name",
        help="Name of the CRD defined in metadata.name",
        type=str,
        required=False,
    )
    parser.add_argument(
        "--version",
        help="Version of the schema in the CRD",
        type=str,
        required=False,
    )
    args = parser.parse_args()

    with open(args.crd_file, "r", encoding="utf-8") as crd_file:
        documents = yaml.load_all(crd_file, Loader=yaml.FullLoader)

        crd_candidates = {}
        for document in documents:
            if "kind" in document:
                if document["kind"] == "CustomResourceDefinition":
                    crd_candidates[document["metadata"]["name"]] = document
                    break
            else:
                raise RuntimeError("Document contains no-Kubernetes objects")

    if crd_candidates:
        if args.crd_name is not None and args.crd_name not in crd_candidates:
            logging.error(
                "CRD %s not found, available CRDs: %s",
                args.crd_name,
                str(crd_candidates.keys()),
            )
            sys.exit(1)

        if len(crd_candidates) > 1:
            if args.crd_name is None:
                logging.error(
                    "Multiple CRDs found, please specify one through the --crd-name argument"
                )
                logging.error("Available CRDs: %s", str(crd_candidates.keys()))
                sys.exit(1)
            else:
                crd = crd_candidates[args.crd_name]
        else:
            crd = list(crd_candidates.values())[0]

    if args.version is None:
        if len(crd["spec"]["versions"]) > 1:
            logging.warning(
                "Multiple versions found in CRD, using the latest version"
            )
        raw_schema = crd["spec"]["versions"][-1]["schema"]["openAPIV3Schema"]
    else:
        for version in crd["spec"]["versions"]:
            if version["name"] == args.version:
                raw_schema = version["schema"]["openAPIV3Schema"]
                break
        else:
            raise RuntimeError(f"Version {args.version} not found in CRD")

    print(
        "Total number of schema nodes in the CRD:",
        get_total_number_schemas(raw_schema),
    )


if __name__ == "__main__":
    main()
