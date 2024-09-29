import openai
import argparse
import os
import json

def read_missing_properties(path):
    path = os.path.join(path, "missing_fields.json")
    with open(path, 'r') as f:
        missing_properties = json.load(f)

    resutls = []
    for i in range(len(missing_properties)):
        prop = missing_properties[i]
        if prop[2] == "array":
            continue
            
        resutls.append(f"- {prop[0]}\n description: {prop[1]}\n type: {prop[2]}\n structure: {prop[3]}\n")

    return resutls

def gen_values(missing_values, path, api_key, operator):
    openai.api_key = api_key

    context = f"You are a expert of the {operator} of the Kubernetes ecosystem. You are tasked with providing values for properties of the {operator} CRD"

    prompt = "Here are the properties that need values:\n"
    for prop in missing_values:
        prompt += f"{prop}\n"

    prompt += "\nEach properties has a datatype and description provided above, please make sure the generated value satisfies the datatype and description.\n"

    prompt += "\nFor the properties that have structure that indicating subfields, make sure to generate all the subfields for those properties as a whole.\n"

    prompt += "\nProvide three values for each property and follwoing the format below:\n"

    format = "\{\"property1\": [\"value1\", \"value2\", \"value3\"]\}\n\n"

    prompt += format

    completion = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]
    )
    
    result_text = completion.choices[0].message.content

    output_file = os.path.join(path, "values_for_missing_properties.txt")
    with open(output_file, 'w') as f:
        f.write(result_text)

    output_file = os.path.join(path, "values_for_missing_properties.json")
    with open(output_file, 'w') as f:
        json.dump(result_text, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, help="Path to the file containing the missing properties")
    parser.add_argument("--api_key", type=str, help="API key for the OpenAI API")
    parser.add_argument("--operator", type=str, help="Name of the operator")
    args = parser.parse_args()

    missing_properties = read_missing_properties(args.path)
    
    gen_values(missing_properties, args.path, args.api_key, args.operator)
