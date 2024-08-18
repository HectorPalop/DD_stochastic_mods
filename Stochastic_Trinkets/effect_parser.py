import json
import os

def load_effect_types(json_data):
    with open(json_data, 'r') as file:
            effect_types = json.load(file)
    return effect_types

def append_buffs_to_json(new_buffs, filename):
    data = {"buffs": []}
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        try:
            with open(filename, 'r') as file:
                data = json.load(file)
        except json.JSONDecodeError:
            print(f"Error reading {filename}. File might be corrupted. Starting with empty buffs list.")
    if "buffs" in data:
        data["buffs"].extend(new_buffs)
    else:
        data["buffs"] = new_buffs
    with open(filename, 'w') as file:
        json.dump(data, file, indent=3)

def get_effect_entry(effect_types, effect_name, detail_key):
    if effect_name in effect_types:
        effect_details = effect_types[effect_name]
        if effect_details and len(effect_details) > 0:
            if detail_key in effect_details[0]:
                return effect_details[0][detail_key]
    return None

def parse_effects(LLM_buffs_dict, LLM_trinket_name, modded_json_filename):
    json_file_path = os.path.join(script_dir, 'effect_types.json')
    effect_types = load_effect_types(json_file_path)
    i=0
    buff_list=[]
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
    modded_json_filepath = os.path.join(script_dir, modded_json_filename)
    append_buffs_to_json(buff_list, modded_json_filepath)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    LLM_buffs_dict = {'Bleed Resist': '-5', 'Damage': '+15'}
    LLM_trinket_name = 'Starweave Pendant'
    modded_json_filename = 'modded_buffs.json'

    parse_effects(LLM_buffs_dict, LLM_trinket_name, modded_json_filename)

    


             
             



# Note: make exception for damage (low, high)
