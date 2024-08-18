import json
import os

def extract_entries_with_param(json_data, param):
    names = {}
    
    for effect in json_data['buffs']:
        name = effect.get(param)
        if name:
            names[name] = name
    
    return names

if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Path to the JSON file
    json_file_path = os.path.join(script_dir, 'vanilla_trinket_buffs.json')
    
    # Load JSON data from file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Extract names
    parameter_to_extract = 'stat_type'
    stat_types = extract_entries_with_param(data, parameter_to_extract)
    print ("STAT TYPES: ", stat_types.values())

    parameter_to_extract = 'stat_sub_type'
    stat_sub_types = extract_entries_with_param(data, parameter_to_extract)
    print ("STAT SUBTYPES: ", stat_sub_types.values())