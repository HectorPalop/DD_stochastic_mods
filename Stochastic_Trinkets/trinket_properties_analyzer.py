import json
import os

def get_unique_ids(data):
    ids = {entry['id'] for entry in data['entries']}
    return list(ids)

if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Path to the JSON file
    json_file_path = os.path.join(script_dir, '..', 'DarkestDungeon', 'trinkets', 'base.entries.trinkets.json')
    
    # Open the JSON file and read its content
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Get unique ids from the data
    unique_ids = get_unique_ids(data)
    print(f"unique_ids [{len(unique_ids)}] : {unique_ids}")