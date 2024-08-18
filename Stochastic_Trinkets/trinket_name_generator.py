import json
import os
import ollama

def get_unique_ids_from_file(json_file_path):
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    ids = {entry['id'] for entry in data['entries']}
    return list(ids)

def make_trinket_name_system_prompt(model, temp, trinket_list):
    from_line = "FROM " + model
    parameter_line = "PARAMETER temperature " + temp
    system_line_header = (
        "SYSTEM "
        "You are tasked with deciding names of gamefiles in the video game Darkest Dungeon. "
        "Answer only with ONE plausible name for the game file and NOTHING ELSE. "
        "Choose a name that is in line with the themes of the game (dark fantasy, lovecraftian). "
        "Choose a name that is different but in the same format as any in the following list:"
    )
    trinket_list_text = " ".join(trinket_list)

    trinket_namer_modelfile = f'''
    {from_line}
    {parameter_line}
    {system_line_header}{trinket_list_text}
    '''
    return trinket_namer_modelfile.strip()

def generate_name(json_file_path):
    unique_ids = get_unique_ids_from_file(json_file_path)
    trinket_namer_modelfile = make_trinket_name_system_prompt(model='llama3:8b', temp='0.9', trinket_list=unique_ids)
    ollama.create(model='trinket_namer', modelfile=trinket_namer_modelfile)
    print('model loaded')
    response = ollama.chat(model='trinket_namer', messages=[
    {
        'role': 'user',
        'content': 'Please suggest a unique trinket name. Answer only with ONE plausible name for the game file and NOTHING ELSE.',
    },
    ])
    return(response['message']['content'])

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    json_file_path = os.path.join(script_dir, '..', 'DarkestDungeon', 'trinkets', 'base.entries.trinkets.json')
    gen_trinket_name = generate_name(json_file_path)
    print (gen_trinket_name)

    