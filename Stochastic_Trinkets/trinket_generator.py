import json
import os
import ollama
import ast
import re

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

def generate_trinket_name(json_file_path):
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
    gen_name = response['message']['content']
    cleaned_gen_name = gen_name.replace('"', "")
    return cleaned_gen_name

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
        "Choose concrete numerical values, not just ranges of values. "
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
    trinket_namer_modelfile = choose_trinket_stats_system_prompt(model='llama3:8b', temp='0.7', stat_list=vanilla_stats, trinket_name=trinket_name)
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
    trinket_tuner_modelfile = tune_trinket_stats_system_prompt(model='llama3:8b', temp='0.7', stat_list=trinket_bounds, trinket_name=trinket_name)
    ollama.create(model='stat_tuner', modelfile=trinket_tuner_modelfile)
    print('stat tuner model loaded')
    response = ollama.chat(model='stat_tuner', messages=[
    {
        'role': 'user',
        'content': 'STATS: ' + str(stat_names) + ' Please answer ONLY with the completed dictionary and NOTHING ELSE.',
    },
    ])
    return response['message']['content']

def load_effect_types(json_data):
    with open(json_data, 'r') as file:
            effect_types = json.load(file)
    return effect_types

def append_entries_to_json(new_buffs, filename, type):
    data = {type: []}
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        try:
            with open(filename, 'r') as file:
                data = json.load(file)
        except json.JSONDecodeError:
            print(f"Error reading {filename}. File might be corrupted. Starting with empty buffs list.")
    if type in data:
        data[type].extend(new_buffs)
    else:
        data[type] = new_buffs
    with open(filename, 'w') as file:
        json.dump(data, file, indent=3)

def get_effect_entry(effect_types, effect_name, detail_key):
    if effect_name in effect_types:
        effect_details = effect_types[effect_name]
        if effect_details and len(effect_details) > 0:
            if detail_key in effect_details[0]:
                return effect_details[0][detail_key]
    return None

def parse_gen_trinket_buffs(LLM_buffs_dict_string, LLM_trinket_name, effect_types_json_filepath, modded_json_filepath):
    effect_types = load_effect_types(effect_types_json_filepath)
    i=0
    buff_list=[]
    LLM_buffs_dict = ast.literal_eval(LLM_buffs_dict_string)
    for LLM_buff in LLM_buffs_dict.keys():
        i+=1
        buff = {}
        buff['id'] = "TRINKET_"+LLM_trinket_name.replace(" ", "_")+"_BUFF"+str(i)
        buff['stat_type'] = get_effect_entry (effect_types, LLM_buff, 'stat_type')
        if LLM_buff == 'Damage':
            buff['stat_sub_type'] = "damage_low"
        else:
            buff['stat_sub_type'] = get_effect_entry (effect_types, LLM_buff, 'stat_subtype')
        if get_effect_entry (effect_types, LLM_buff, 'magnitude_type') == "percent":
             buff['amount'] = float(LLM_buffs_dict[LLM_buff])/100
        else:
             buff['amount'] = float(LLM_buffs_dict[LLM_buff])
        if LLM_buff == 'Death Blow':
            buff['amount'] = -buff['amount']
        buff['remove_if_not_active'] = False
        buff['rule_type'] = "always"
        buff['is_false_rule'] = False
        buff['rule_data'] = {"float" : 0, "string" : ""}
        buff_list.append(buff)
        if LLM_buff == 'Damage':
            buff2 = buff.copy()
            i+=1
            buff2['id'] = "TRINKET_"+LLM_trinket_name.replace(" ", "_")+"_BUFF"+str(i)
            buff2['stat_sub_type'] = "damage_high"
            buff_list.append(buff2)
    append_entries_to_json(buff_list, modded_json_filepath, "buffs")
    list_of_ids = [e["id"] for e in buff_list]
    return list_of_ids

def parse_gen_trinket_entry(trinket_name, trinket_buffs, modded_entries_filepath):
    trinket_entry = {}
    trinket_entry["id"] = trinket_name
    trinket_entry["buffs"] = trinket_buffs
    trinket_entry["hero_class_requirements"] = []
    trinket_entry["rarity"] = "uncommon"
    trinket_entry["price"] = 10000
    trinket_entry["limit"] = 1
    trinket_entry["origin_dungeon"] = ""
    append_entries_to_json([trinket_entry], modded_entries_filepath, "entries")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    vanilla_trinkets_filepath = os.path.join(script_dir, '..', 'DarkestDungeon', 'trinkets', 'base.entries.trinkets.json')
    gen_trinket_name = generate_trinket_name(vanilla_trinkets_filepath)

    print ('trinket name ->', gen_trinket_name)

    trinket_effects_filepath = os.path.join(script_dir, 'trinket_effects.json')
    gen_trinket_stats = generate_trinket_stats(trinket_effects_filepath, gen_trinket_name)

    print ('trinket stats ->', gen_trinket_stats)

    effect_types_json_filename = os.path.join(script_dir, 'effect_types.json')
    modded_trinket_buffs_filename = os.path.join(script_dir, 'modded_buffs.json')
    buff_names = parse_gen_trinket_buffs(gen_trinket_stats, gen_trinket_name, effect_types_json_filename, modded_trinket_buffs_filename)

    modded_trinket_entries_filename = os.path.join(script_dir, 'modded_trinket_entries.json')
    parse_gen_trinket_entry(gen_trinket_name, buff_names, modded_trinket_entries_filename)