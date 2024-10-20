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
        output_file = os.path.join(path, f"value_{p}.json")
        if datatype == "boolean":
            result = {p : {"valid_value1": True, "valid_value2": False, "invalid_value": "N/A"}}
            with open(output_file, "w") as f:
                json.dump(result, f, indent=4)

        else:
            continue
            prop = f"property: {p}\n description: {description}\n type: {datatype}\n default: {default}\n"

            prompt = "Here is the property that need values:\n"
            prompt += f"{prop}\n"

            prompt += "\nThe property has a datatype and description provided above, for valid values, please make sue that the values satisfy the datatype and description. For invalid value, please make sure it also satisfy the datatype but to be an erroneous one.\n"

            prompt += "\n\nProvide two valid values for the property and one invalid value that satisfies the type, but to be an erroneous value\n. Please follow the following fomart strictly so that it can be write to the json file directly, for example\n"

            format= "```json\n"
            format += "{\n"
            format += f"  \"{p}\": " +  "{\n"
            format += f"    \"valid_value1\": value1\n"
            format += f"    \"valid_value2\": value2\n"
            format += f"    \"invalid_value\": value3"
            format += "  }\n"
            format += "}\n"
            format += "```"

            prompt += format

            completion = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": prompt},
                ],
            )

            result_text = completion.choices[0].message.content
            

            result = result_text.split("```json\n")[1].split("```")[0]
            with open(output_file, "w") as f:
                f.write(result)


def collect_result(path, file_name):
    main_results = {}

    for file in glob.glob(os.path.join(path, "*.json"), recursive=True):
        if file == os.path.join(path, file_name):
            continue
        print(file)
        with open(file, "r") as f:
            content = json.load(f)
            main_results.update(content)
    with open(os.path.join(path, "config_values.json"), "w") as f:
        json.dump(main_results, f, indent=4)


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
    collect_result(args.path, args.file_name)