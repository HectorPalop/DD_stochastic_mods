import json
import os

def extract_names(json_data):
    names = {}
    
    for effect in json_data['effects']:
        name = effect.get('name')
        if name:
            names[name] = name
    
    return names

def main():
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Path to the JSON file
    json_file_path = os.path.join(script_dir, 'trinket_effects.json')
    
    # Load JSON data from file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Extract names
    names = extract_names(data)

    # Print the result
    print (names.values())

if __name__ == "__main__":
    main()