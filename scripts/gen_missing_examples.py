import openai
import argparse
import os
import json
import yaml
import glob

def read_missing_properties(path):
    path = os.path.join(path, "missing_fields.json")
    with open(path, 'r') as f:
        missing_properties = json.load(f)

    return missing_properties

def gen_values(missing_values, path, api_key, operator):
    openai.api_key = api_key

    context = f"You are a expert of the {operator} of the Kubernetes ecosystem. You are tasked with providing values for properties of the {operator} CRD"

    for i in range(len(missing_values)):
        p = missing_values[i]

        if p[0].endswith("ITEM"):
            continue
            
        prop = f"- {p[0]}\n description: {p[1]}\n type: {p[2]}\n structure: {p[3]}\n"

        prompt = "Here is the property that need values:\n"
        prompt += f"{prop}\n"

        prompt += "\nThe property has a datatype and description provided above, please make sure the generated value satisfies the datatype and description.\n"

        prompt += "\n If the property has structure that indicating subfields, make sure to generate all the subfields for the property as a whole.\n"

        prompt += "\nProvide three values for the property and please follow the cr yaml format. Directly give me the yaml file without any other message, for example\n"

        format = "spec:\n"
        format += f"  {p[0]}: value\n"
        format += "---"
        format += "spec:\n"
        format += f"  {p[0]}: value\n"

        prompt += format

        prompt += "If the property has `ITEM` in the property path, that means the property should be an item in an array. For example, for \"spec.pdms.ITEM.config:\" the format should be:\n"
        array_format = "spec:\n"
        array_format += f"  property:\n"
        array_format += "   - subproperty: value\n"
        array_format += "   - subproperty: value\n"
        array_format += "   - subproperty: value\n"

        prompt += array_format

        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ]
        )
        
        result_text = completion.choices[0].message.content

        result = result_text.split("```yaml\n")[1].split("```")[0]

        output_file = os.path.join(path, f"value_{p[0]}.yaml")
        with open(output_file, 'w') as f:
            f.write(result)

def store_to_examples(path):
    main_results = []

    for file in glob.glob(
        os.path.join(path, "*.yaml"), recursive=True):
        if file == "examples.yaml":
            continue
        with open(file, 'r') as f:
            content = yaml.safe_load_all(f)
            for doc in content:
                main_results.append(doc)
    with open(os.path.join(path, "examples.yaml"), 'w') as f:
        yaml.dump_all(main_results, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, help="Path to the file containing the missing properties")
    parser.add_argument("--api_key", type=str, help="API key for the OpenAI API")
    parser.add_argument("--operator", type=str, help="Name of the operator")
    args = parser.parse_args()

    missing_properties = read_missing_properties(args.path)
    
    gen_values(missing_properties, args.path, args.api_key, args.operator)
    store_to_examples(args.path)
