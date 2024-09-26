import openai
import argparse
import os
import json
from openai import OpenAI

def read_missing_properties(path):
    with open(path, 'r') as f:
        missing_properties = json.load(f)
    for i in range(len(missing_properties)):
        description =  "\ndescription: "
        if missing_properties[i][-1]:
            description += missing_properties[i][-1]
        else:
            description += "No description available"
        missing_properties[i] = '.'.join(missing_properties[i][:-1])
        missing_properties[i] += description + "\n"

    return missing_properties

def gen_values(missing_values, path, api_key, operator):
    openai.api_key = api_key
    client = OpenAI(api_key)

    context = f"You are a expert of the {operator} of the Kubernetes ecosystem. You are tasked with providing values for properties of the {operator} CRD"

    prompt = "Here are the properties that need values:\n"
    for prop in missing_values:
        prompt += f"- {prop}\n"

    prompt += "\nProvide three values for each property and follwoing the format below:\n"

    format = "\{\"property1\": [\"value1\", \"value2\", \"value3\"]\}\n\n"

    prompt += format

    prompt += "Here are some examples:\n"

    exmaples = "\{\}"
    prompt += exmaples

    completion = client.chat.completions.create(
        model="o1-preview",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]
    )
    
    result_text = completion.choices[0].message.content
    result_lines = result_text.split("\n")
    result_dict = {}
    
    # TODO: modify the results processing part
    for prop, value in zip(missing_values, result_lines):
        result_dict[prop] = value.strip("- ")

    output_file = os.path.join(path, "values_for_missing_properties.json")
    with open(output_file, 'w') as f:
        json.dump(result_dict, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, help="Path to the file containing the missing properties")
    # parser.add_argument("--api_key", type=str, help="API key for the OpenAI API")
    # parser.add_argument("--operator", type=str, help="Name of the operator")
    args = parser.parse_args()

    missing_properties = read_missing_properties(args.path)
    prompt = "Here are the properties that need values:\n"
    for prop in missing_properties:
        prompt += f"- {prop}\n"
    print(prompt)
    
    # gen_values(missing_properties, args.path, args.api_key)
