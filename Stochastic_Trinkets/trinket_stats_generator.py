import json
import os
import ollama
import ast
import re

def parse_effects(LLM_effects, vanilla_stats):
    try:
        parsed_effects = LLM_effects.strip('[]').split(', ')
    except:
        try:
            preparsed_effects = ast.literal_eval(LLM_effects)
            parsed_effects = f"[{', '.join(preparsed_effects)}]"
        except:
            print('incorrect python format. Re-attempting...')
            return False
    if not all(effect[1:].strip() in vanilla_stats for effect in parsed_effects):
        print('some effect was not recognized. Re-attempting...')
        return False
    else:
        result_dict = {}
        for item in parsed_effects:
            sign = item[0]
            key = item[1:].strip()
            result_dict[key] = sign
        return result_dict

def extract_names(json_file_path):
    json_file_path = os.path.join(script_dir, json_file_path)
    with open(json_file_path, 'r') as file:
        json_data = json.load(file)
    names = []
    for effect in json_data['effects']:
        name = effect.get('name')
        if name:
            names.append(name)
    return names

def load_json_to_string(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    json_string = json.dumps(data, separators=(',', ':'))
    json_string = re.sub(r'([,:])(?![\d\s])', r'\1 ', json_string)
    return json_string

def choose_trinket_stats_system_prompt(model, temp, stat_list, trinket_name):
    from_line = "FROM " + model
    parameter_line = "PARAMETER temperature " + temp
    system_line_header = (
        "SYSTEM "
        "You are tasked with deciding the effects from trinkets in the video game Darkest Dungeon. "
        "You should choose stats that are representative of the trinket's title, which is: " + trinket_name + ". "
        "Choose a minimum of 1 and a maximum of 5 stats. Balance positive with negative effects."
        "Precede each stat with either a + or a - depending on whether the effect is positive or negative."
        "EACH STAT SHOULD BE ONE OF THE FOLLOWING LIST (WRITE THEM EXACTLY AS THEY APPEAR HERE):"
    )
    trinket_list_text = " ".join(stat_list)
    trinket_namer_modelfile = f'''
    {from_line}
    {parameter_line}
    {system_line_header}{trinket_list_text}
    '''
    return trinket_namer_modelfile.strip()

def tune_trinket_stats_system_prompt(model, temp, stat_list, trinket_name):
    from_line = "FROM " + model
    parameter_line = "PARAMETER temperature " + temp
    system_line_header = (
        "SYSTEM "
        "You are tasked with tuning the values of the effects from trinkets in the video game Darkest Dungeon. "
        "The trinket you are currently analyzing is: " + trinket_name + ". "
        "The user will give you a python dictionary. "
        "The keys of the dictionnary are the names of the stats from the trinket. "
        "The values of the dictionnary are + and - symbols, representing whether the stat should be positive or negative. "
        "Your task is incorporating numerical values to these stats as values in the dictionnary. "
        "The maximum and minimum magnitudes for each stat are given below in a json file. "
        "EXAMPLE: "
        "user: STATS: {'Bleed Resist': '-', 'Healing Received': '+', 'Stress': '-'} Please answer ONLY with the completed dictionary and NOTHING ELSE. "
        "expected output: {'Bleed Resist': '-10', 'Healing Received': '+30', 'Stress': '-20'} "
        "JSON FILE DETAILING THE MAXIMUM AND MINIMUM MAGNITUDES FOR EACH STAT: " + stat_list + ""
    )    
    trinket_tuner_modelfile = f'''
    {from_line}
    {parameter_line}
    {system_line_header}
    '''
    return trinket_tuner_modelfile.strip()

def generate_trinket_stats(json_file_path, trinket_name):
    vanilla_stats = extract_names(json_file_path)
    trinket_namer_modelfile = choose_trinket_stats_system_prompt(model='llama3.1:8b', temp='0.7', stat_list=vanilla_stats, trinket_name=trinket_name)
    ollama.create(model='trinket_namer', modelfile=trinket_namer_modelfile)
    print('stat namer model loaded')
    stat_names = False
    while stat_names == False:
        response = ollama.chat(model='trinket_namer', messages=[
        {
            'role': 'user',
            'content': 'Please suggest a list of trinket stats. Answer ONLY with a python list with these stats and NOTHING ELSE.',
        },
        ])
        print('LLM answer:', response['message']['content'])
        stat_names = parse_effects(response['message']['content'], vanilla_stats)
    print('parsed stats:', stat_names)
    trinket_bounds = load_json_to_string(json_file_path)
    trinket_tuner_modelfile = tune_trinket_stats_system_prompt(model='llama3.1:8b', temp='0.7', stat_list=trinket_bounds, trinket_name=trinket_name)
    ollama.create(model='stat_tuner', modelfile=trinket_tuner_modelfile)
    print('stat tuner model loaded')
    response = ollama.chat(model='stat_tuner', messages=[
    {
        'role': 'user',
        'content': 'STATS: ' + str(stat_names) + ' Please answer ONLY with the completed dictionary and NOTHING ELSE.',
    },
    ])
    return(response['message']['content'])

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(script_dir, 'trinket_effects.json')

    placeholder_trinket_name = "Moonwhisper's Tear"

    gen_trinket_stats = generate_trinket_stats(json_file_path, placeholder_trinket_name)
    print (gen_trinket_stats)

    

    

    
    