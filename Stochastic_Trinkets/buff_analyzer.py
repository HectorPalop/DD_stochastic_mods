import json
from collections import defaultdict
import os

def extract_unique_values(json_data):
    unique_values = defaultdict(set)
    
    for buff in json_data['buffs']:
        for key, value in buff.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    unique_values[f"{key}.{sub_key}"].add(sub_value)
            else:
                unique_values[key].add(value)
    
    # Convert sets to lists for final output
    unique_values = {key: list(values) for key, values in unique_values.items()}
    
    return unique_values

def main():
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Path to the JSON file
    json_file_path = os.path.join(script_dir, 'vanilla_trinket_buffs.json')
    
    # Load JSON data from file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Extract unique values
    unique_values = extract_unique_values(data)

    # Print the result
    for key, values in unique_values.items():
        print(f"{key} [{len(values)}] : {values}\n")

if __name__ == "__main__":
    main()