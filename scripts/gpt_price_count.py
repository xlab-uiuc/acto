import tiktoken
import argparse
import json
import os

def encoding_getter(encoding_type: str):
    """
    Returns the appropriate encoding based on the given encoding type (either an encoding string or a model name).
    """
    if "k_base" in encoding_type:
        return tiktoken.get_encoding(encoding_type)
    else:
        return tiktoken.encoding_for_model(encoding_type)

def tokenizer(string: str, encoding_type: str) -> list:
    """
    Returns the tokens in a text string using the specified encoding.
    """
    encoding = encoding_getter(encoding_type)
    tokens = encoding.encode(string)
    return tokens

def token_counter(string: str, encoding_type: str) -> int:
    """
    Returns the number of tokens in a text string using the specified encoding.
    """
    num_tokens = len(tokenizer(string, encoding_type))
    return num_tokens

def read_missing_properties(path):
    path = os.path.join(path, "missing_fields.json")
    with open(path, "r", encoding="utf-8") as f:
        missing_properties = json.load(f)

    return missing_properties

def input_tokens(missing_values, path, operator):

    context = f"You are a expert of the {operator} of the Kubernetes ecosystem. You are tasked with providing values for properties of the {operator} CRD"
    
    context_tokens = 0
    prompt_tokens = 0

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

        prompt += 'If the property has `ITEM` in the property path, that means the property should be an item in an array. For example, for "spec.pdms.ITEM.config:" the format should be:\n'
        array_format = "spec:\n"
        array_format += f"  property:\n"
        array_format += "   - subproperty: value\n"
        array_format += "   - subproperty: value\n"
        array_format += "   - subproperty: value\n"

        prompt += array_format

        context_tokens += token_counter(context, "o200k_base")
        prompt_tokens += token_counter(prompt, "o200k_base")

    return context_tokens, prompt_tokens

def output_tokens(path):
    output = 0
    for file in os.listdir(path):
        if file.endswith(".yaml") and file != "examples.yaml":
            with open(os.path.join(path, file), "r", encoding="utf-8") as f:
                data = "```yaml\n" + f.read() + "```"
                output += token_counter(data, "o200k_base")
    return output
            
def calculate_price(context, prompt, output):
    context_price = context * 2.50 / 10000000
    prompt_price = prompt * 2.50 / 10000000
    output_price = output * 10.00 / 10000000
    return context_price + prompt_price + output_price

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=str,
        help="Path to the file containing the missing properties",
    )
    parser.add_argument("--operator", type=str, help="Name of the operator")
    args = parser.parse_args()

    missing_properties = read_missing_properties(args.path)

    context, prompt = input_tokens(missing_properties, args.path, args.operator)
    output = output_tokens(args.path)
    
    price = calculate_price(context, prompt, output)

    print(f"Context tokens: {context}")
    print(f"Prompt tokens: {prompt}")
    print(f"Output tokens: {output}")
    print(f"Price: ${price}")

