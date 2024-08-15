import json
import os
import ollama
import ast

def parse_effects(LLM_effects, vanilla_stats):
    try:
        parsed_effects = LLM_effects.strip('[]').split(', ')
    except:
        try:
            preparsed_effects = ast.literal_eval(LLM_effects)
            parsed_effects = f"[{', '.join(preparsed_effects)}]"
        except:
            print('incorrect python format')
            return False
    if not all(effect[1:].strip() in vanilla_stats for effect in parsed_effects):
        print('effect not recognized:')
        for effect in parsed_effects:
            print (effect[1:].strip())
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

def make_trinket_stats_system_prompt(model, temp, stat_list, trinket_name):
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

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(script_dir, 'trinket_effects.json')
    vanilla_stats = extract_names(json_file_path)
    print(f"vanilla_stats [{len(vanilla_stats)}] : {vanilla_stats}")

    trinket_name_placeholder = "Moonwhisper's Tear"
    trinket_namer_modelfile = make_trinket_stats_system_prompt(model='llama3:8b', temp='0.7', stat_list=vanilla_stats, trinket_name=trinket_name_placeholder)
    # print (trinket_namer_modelfile)

    ollama.create(model='trinket_namer', modelfile=trinket_namer_modelfile)
    print('model loaded')

    response = ollama.chat(model='trinket_namer', messages=[
    {
        'role': 'user',
        'content': 'Please suggest a list of trinket stats. Answer ONLY with a python list with these stats and NOTHING ELSE.',
    },
    ])
    print(response['message']['content'])
    print(parse_effects(response['message']['content'], vanilla_stats))


    