import argparse
import glob
import json
import os

import openai


def read_config(path, file_name):
    file_path = os.path.join(path, file_name)
    with open(file_path, "r", encoding="utf-8") as f:
        config_schema = json.load(f)
    leaf_properties = {}
    for prop in config_schema["properties"]:
        leaf_properties.update(rec_search(prop, config_schema["properties"][prop]))
    return leaf_properties

def rec_search(prev_name, property):
    if property["type"] != "object":
        if property["type"] == "boolean":
            return {}
        return {prev_name: {"description": property["description"], "type": property["type"],"default": property["default"]}}
    else:
        leaf_properties = {}
        for prop in property["properties"]:
            leaf_properties.update(rec_search(prev_name + "." + prop, property["properties"][prop]))
        return leaf_properties


def gen_values(properties, path, api_key, application):
    openai.api_key = api_key

    context = f"You are a expert of the {application}. You are tasked with providing values for properties of the {application} configuration file"

    for p in properties:
        info = properties[p]
        description = info["description"]
        datatype = info["type"]
        default = info["default"]

        prop = f"property: {p}\n description: {description}\n type: {datatype}\n default: {default}\n"

        prompt = "Here is the property that need values:\n"
        prompt += f"{prop}\n"

        prompt += "\nThe property has a datatype and description provided above, for valid values, please make sue that the values satisfy the datatype and description. For invalid value, please make sure it also satisfy the datatype but to be an erroneous one.\n"

        prompt += "\n\nProvide two valid values for the property and one invalid value that satisfies the type, but to be an erroneous value\n. Directly give me the value in json format without any other message, for example\n"

        format = f"property: {p}:\n"
        format += f"  valid_value1: value1\n"
        format += f"  valid_value2: value2\n"
        format += f"  invalid_value: value3\n"

        prompt += format

        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": prompt},
            ],
        )

        result_text = completion.choices[0].message.content
        print(result_text)

        result = result_text.split("```json\n")[1].split("```")[0]

        output_file = os.path.join(path, f"value_{p}.json")
        with open(output_file, "w") as f:
            f.write(result)


# def store_to_examples(path):
#     main_results = []

#     for file in glob.glob(os.path.join(path, "*.yaml"), recursive=True):
#         if file == "examples.yaml":
#             continue
#         with open(file, "r") as f:
#             content = yaml.safe_load_all(f)
#             for doc in content:
#                 main_results.append(doc)
#     with open(os.path.join(path, "examples.yaml"), "w") as f:
#         yaml.dump_all(main_results, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=str,
        help="Path to the configuration file",
    )
    parser.add_argument("--file_name", type=str, help="Name of the configuration file")
    parser.add_argument(
        "--api_key", type=str, help="API key for the OpenAI API"
    )
    parser.add_argument("--application", type=str, help="Name of the application")

    args = parser.parse_args()

    config_schema = read_config(args.path, args.file_name)

    gen_values(config_schema, args.path, args.api_key, args.application)
    # store_to_examples(args.path)