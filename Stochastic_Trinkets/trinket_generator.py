import json
import os
import ollama
import ast
import re
from diffusers import StableDiffusionPipeline, DDPMScheduler, EulerDiscreteScheduler
from scipy.ndimage import gaussian_filter
import numpy as np
from PIL import Image
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

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
        "Favor darker themes, and avoid the word 'whisper'. "
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
    trinket_namer_modelfile = make_trinket_name_system_prompt(model='llama3.1:8b', temp='0.9', trinket_list=unique_ids)
    ollama.create(model='DD_trinket_namer', modelfile=trinket_namer_modelfile)
    print('DD_trinket_namer model loaded')
    response = ollama.chat(model='DD_trinket_namer', keep_alive=0, messages=[
    {
        'role': 'user',
        'content': 'Please suggest a unique trinket name. Avoid the word whisper. Answer only with ONE plausible name for the game file and NOTHING ELSE.',
    },
    ])
    gen_name = response['message']['content']
    cleaned_gen_name = gen_name.replace('"', "")
    return cleaned_gen_name

def parse_effects(LLM_effects, vanilla_stats):
    try:
        preparsed_effects = LLM_effects.strip('[]').split(', ')
        parsed_effects = [item.strip("'") for item in preparsed_effects]
    except:
        try:
            preparsed_effects = ast.literal_eval(LLM_effects)
            parsed_effects = f"[{', '.join(preparsed_effects)}]"
        except:
            print('incorrect python format. Re-attempting...')
            return False
    print (parsed_effects)
    if not all(effect[1:].strip() in vanilla_stats for effect in parsed_effects):
        print('some effect was not recognized. Re-attempting...')
        for effect in parsed_effects:
            if effect[1:].strip() not in vanilla_stats:
                print ("effect not in vanilla stats:", effect[1:].strip())
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

def choose_trinket_stats_system_prompt(model, temp, stat_list, trinket_name, trinket_rarity, trinket_class):
    from_line = "FROM " + model
    parameter_line = "PARAMETER temperature " + temp
    system_line_header = (
        "SYSTEM "
        "You are tasked with deciding the effects from trinkets in the video game Darkest Dungeon. "
        "You should choose stats that are representative of the trinket's title, which is: " + trinket_name + ". "
        "The rarity of the trinket is " + trinket_rarity.replace('_', " ") + " and it is useable by " + trinket_class.replace('_', " ") + ". "
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

def tune_trinket_stats_system_prompt(model, temp, stat_list, trinket_name, trinket_rarity, trinket_class):
    from_line = "FROM " + model
    parameter_line = "PARAMETER temperature " + temp
    system_line_header = (
        "SYSTEM "
        "You are tasked with tuning the values of the effects from trinkets in the video game Darkest Dungeon. "
        "The trinket you are currently analyzing is: " + trinket_name + ". "
        "The rarity of the trinket is " + trinket_rarity.replace('_', " ") + " and it is useable by " + trinket_class.replace('_', " ") + ". "
        "More rare and class-specific trinkets have more potent effects (both positive and negative), whereas common trinkets are weaker. "
        "The user will give you a python dictionary. "
        "The keys of the dictionnary are the names of the stats from the trinket. "
        "The values of the dictionnary are + and - symbols, representing whether the stat should be positive or negative. "
        "Your task is incorporating numerical values to these stats as values in the dictionnary. "
        "The names of the stats that you write should be the exactly the same as the ones provided by the user. "
        "For each of those stats, choose concrete numerical values, not just ranges of values. "
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

def generate_trinket_stats(json_file_path, trinket_name, trinket_rarity, trinket_class):
    vanilla_stats = extract_names(json_file_path)
    trinket_namer_modelfile = choose_trinket_stats_system_prompt('llama3.1:8b', '0.7', vanilla_stats, trinket_name, trinket_rarity, trinket_class)
    stat_names = False
    while stat_names == False:
        ollama.create(model='DD_trinket_namer', modelfile=trinket_namer_modelfile)
        print('DD_trinket_namer model loaded')
        response = ollama.chat(model='DD_trinket_namer', keep_alive=0, messages=[
        {
            'role': 'user',
            'content': 'Please suggest a list of trinket stats. Answer ONLY with a python list with these stats and NOTHING ELSE.',
        },
        ])
        print('LLM answer:', response['message']['content'])
        stat_names = parse_effects(response['message']['content'], vanilla_stats)
    print('parsed stats:', stat_names)
    trinket_bounds = load_json_to_string(json_file_path)
    trinket_tuner_modelfile = tune_trinket_stats_system_prompt('llama3.1:8b', '0.7', trinket_bounds, trinket_name, trinket_rarity, trinket_class)
    ollama.create(model='DD_trinket_stat_tuner', modelfile=trinket_tuner_modelfile)
    print('DD_trinket_stat_tuner model loaded')
    response = ollama.chat(model='DD_trinket_stat_tuner', keep_alive=0,  messages=[
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
            buff2['id'] = "TRINKET_"+LLM_trinket_name.replace(" ", "_").replace("'", "").lower()+"_BUFF"+str(i)
            buff2['stat_sub_type'] = "damage_high"
            buff_list.append(buff2)
    append_entries_to_json(buff_list, modded_json_filepath, "buffs")
    list_of_ids = [e["id"] for e in buff_list]
    return list_of_ids

def parse_gen_trinket_entry(trinket_name, trinket_class, trinket_rarity, trinket_buffs, modded_entries_filepath, trinket_properties_filepath):
    with open(trinket_properties_filepath, 'r') as file:
        properties = json.load(file)
    rarities_dict = properties["rarity"]
    trinket_entry = {}
    trinket_entry["id"] = trinket_name.replace(" ", "_").replace("'", "").lower()
    trinket_entry["buffs"] = trinket_buffs
    if trinket_class == 'every_class':
        trinket_entry["hero_class_requirements"] = []
    else:
        trinket_entry["hero_class_requirements"] = [trinket_class]
    trinket_entry["rarity"] = trinket_rarity
    trinket_entry["price"] = rarities_dict[trinket_rarity]
    trinket_entry["limit"] = 1
    trinket_entry["origin_dungeon"] = ""
    append_entries_to_json([trinket_entry], modded_entries_filepath, "entries")

def make_trinket_class_system_prompt(model, temp, trinket_properties, trinket_name):
    from_line = "FROM " + model
    parameter_line = "PARAMETER temperature " + temp
    system_line_header = (
        "SYSTEM "
        "You are tasked with deciding properties of gamefiles in the video game Darkest Dungeon. "
        "More specifically, you will be deciding the hero class (if any) of a trinket in the game, called: " + trinket_name + ". "
        "If this trinket is generic and fits all classes, please just answer the word: every_class. "
        "On the contrary, if this name particularly suits one of the following hero classes, answer with the name of the hero class. "
        "In any case, answer only with either every_class or a class name and NOTHING ELSE. "
        "Here is the list of all the class names in the game: "
    )
    trinket_list_text = " ".join(trinket_properties)

    trinket_class_modelfile = f'''
    {from_line}
    {parameter_line}
    {system_line_header}{trinket_list_text}
    '''
    return trinket_class_modelfile.strip()

def make_trinket_rarity_system_prompt(model, temp, trinket_rarities, trinket_name):
    from_line = "FROM " + model
    parameter_line = "PARAMETER temperature " + temp
    system_line_header = (
        "SYSTEM "
        "You are tasked with deciding properties of gamefiles in the video game Darkest Dungeon. "
        "More specifically, you will be deciding the rarity of a trinket in the game, called: " + trinket_name + ". "
        "Choose a rarity that fits the name of the trinket. "
        "Answer only with the rarity of the trinket and NOTHING ELSE. "
        "Here is the list of all the possible rarities in the game: "
    )
    trinket_list_text = " ".join(trinket_rarities)

    trinket_rarity_modelfile = f'''
    {from_line}
    {parameter_line}
    {system_line_header}{trinket_list_text}
    '''
    return trinket_rarity_modelfile.strip()

def generate_trinket_rarity(json_file_path, trinket_name):
    with open(json_file_path, 'r') as file:
        properties = json.load(file)
    trinket_rarities = properties["rarity"].keys()
    trinket_rarity_modelfile = make_trinket_rarity_system_prompt('llama3.1:8b', '0.9', trinket_rarities, trinket_name)
    gen_name = False
    while (gen_name not in trinket_rarities):
        ollama.create(model='DD_trinket_rarity_namer', modelfile=trinket_rarity_modelfile)
        print('DD_trinket_rarity_namer model loaded')
        response = ollama.chat(model='DD_trinket_rarity_namer', keep_alive=0, messages=[
        {
            'role': 'user',
            'content': 'Please suggest the rarity category for the trinket. Answer only with a valid rarity and NOTHING ELSE.',
        },
        ])
        gen_name = response['message']['content'].replace('"', "").lower()
    return gen_name

def generate_trinket_class(json_file_path, trinket_name):
    with open(json_file_path, 'r') as file:
        properties = json.load(file)
    hero_classes = properties["hero_class_requirements"]
    trinket_class_modelfile = make_trinket_class_system_prompt('llama3.1:8b', '0.9', hero_classes, trinket_name)
    
    gen_name = False
    while (gen_name not in hero_classes) or (gen_name == 'every_class'):  
        ollama.create(model='DD_trinket_class_namer', modelfile=trinket_class_modelfile)
        print('DD_trinket_class_namer model loaded')
        response = ollama.chat(model='DD_trinket_class_namer', keep_alive=0, messages=[
        {
            'role': 'user',
            'content': 'Please suggest the hero class for the trinket. Answer only with either every_class or a class name and NOTHING ELSE.',
        },
        ])
        gen_name = response['message']['content'].replace('"', "").lower()
        if (gen_name not in hero_classes) or (gen_name == 'every_class'):
            print ('invalid class:', gen_name)
    return gen_name

def generate_string_file(xml_file_path, trinket_id, trinket_name, output_file_path):
    if not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
        # Create a new XML structure if the file doesn't exist or is empty
        root = ET.Element("root")
        languages = ["english", "french", "german", "spanish", "brazilian", "russian", 
                     "polish", "czech", "italian", "schinese", "koreanb", "koreana", "japanese"]
        for lang in languages:
            ET.SubElement(root, "language", id=lang)
    else:
        try:
            tree = ET.parse(output_file_path)
            root = tree.getroot()
        except ET.ParseError:
            print(f"Error parsing {output_file_path}. Creating a new XML structure.")
            root = ET.Element("root")
            languages = ["english", "french", "german", "spanish", "brazilian", "russian", 
                         "polish", "czech", "italian", "schinese", "koreanb", "koreana", "japanese"]
            for lang in languages:
                ET.SubElement(root, "language", id=lang)

    # Create the new entry
    new_entry = ET.Element("entry", id=f"str_inventory_title_trinket{trinket_id}")
    new_entry.text = trinket_name

    # Add the new entry to each language
    for language in root.findall('language'):
        language.append(new_entry)
    
    # Use ElementTree for writing with correct XML declaration
    xml_str = ET.tostring(root, encoding='unicode')
    reparsed = minidom.parseString(xml_str)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # Remove excessive newlines while preserving structure
    pretty_xml = re.sub(r'>\n\s+([^<>\s])', r'>\1', pretty_xml)
    pretty_xml = re.sub(r'\n\s*\n', '\n', pretty_xml)
    
    # Ensure UTF-8 encoding in the XML declaration
    pretty_xml = pretty_xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>')
    
    # Wrap content of entry elements with CDATA
    pretty_xml = re.sub(r'<entry([^>]*)>([^<]+)</entry>', r'<entry\1><![CDATA[\2]]></entry>', pretty_xml)
    
    # Write the cleaned-up XML
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

def generate_trinket_entry(trinket_name, xml_file_path, output_file_path):
    trinket_id = trinket_name.replace(" ", "_").replace("'", "").lower()
    generate_string_file(xml_file_path, trinket_id, trinket_name, output_file_path)

def remove_background(image, tolerance=30, blur_radius=5):
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    data = np.array(image)
    edges = np.concatenate([data[0, :], data[-1, :], data[:, 0], data[:, -1]])
    med_color = np.median(edges[:, :3], axis=0)
    distances = np.sqrt(np.sum((data[:,:,:3] - med_color)**2, axis=2))
    mask = distances > tolerance
    mask = gaussian_filter(mask.astype(float), sigma=blur_radius)
    mask = (mask - mask.min()) / (mask.max() - mask.min())
    data[:, :, 3] = (mask * 255).astype(np.uint8)
    result = Image.fromarray(data, mode='RGBA')
    return result

def resize_and_crop(image, target_width, target_height):
    original_width, original_height = image.size
    target_aspect_ratio = target_width / target_height
    original_aspect_ratio = original_width / original_height
    if original_aspect_ratio > target_aspect_ratio:
        new_height = target_height
        new_width = int(new_height * original_aspect_ratio)
    else:
        new_width = target_width
        new_height = int(new_width / original_aspect_ratio)
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    cropped_image = resized_image.crop((left, top, right, bottom))
    return cropped_image

def generate_image(img_name, SD_modelpath, save_dir):
    try:
        pipe = StableDiffusionPipeline.from_single_file(SD_modelpath)
        pipe.to("cuda")
        prompt = f"{img_name}, 2D icon, Darkest Dungeon."
        scheduler = EulerDiscreteScheduler(beta_start=0.00085, beta_end=0.012, beta_schedule="scaled_linear")
        
        image = pipe(
            prompt,
            scheduler=scheduler,
            num_inference_steps=30,
            height=768,
            width=512,
            guidance_scale=7.5,
            safety_checker=None
        ).images[0]
        
        image_rgba = image.convert('RGBA')
        image_no_bg = remove_background(image_rgba)

        image_downsized = resize_and_crop(image_no_bg, 72, 144)
        
        sanitized_img_name = img_name.replace(" ", "_").replace("'", "").lower()
        img_name = f"inv_trinket+{sanitized_img_name}.png"
        image_downsized.save(os.path.join(save_dir, img_name), format='PNG')
    except OSError as e:
        print(f"Error loading Stable Diffusion model: {e}")
        print("Skipping image generation.")
        return

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    vanilla_trinkets_filepath = os.path.join(script_dir, '..', 'DarkestDungeon', 'trinkets', 'base.entries.trinkets.json')
    vanilla_buffs_filepath = os.path.join(script_dir, '..', 'DarkestDungeon', 'shared', 'buffs', 'base.buffs.json')
    vanilla_trinket_imgs_dir = os.path.join(script_dir, '..', 'DarkestDungeon', 'panels', 'icons_equip', 'trinket')

    trinket_properties_filepath = os.path.join(script_dir, 'trinket_properties.json')
    trinket_effects_filepath = os.path.join(script_dir, 'trinket_effects.json')
    effect_types_json_filename = os.path.join(script_dir, 'effect_types.json')
    workshop_xml_filename = os.path.join(script_dir, 'raw_strings_table.xml')
    model_filename = os.path.join(script_dir, "fantassifiedIcons_fantassifiedIconsV20.safetensors")

    modded_trinket_entries_filename = os.path.join(script_dir, 'mod', 'trinkets', 'base.entries.trinkets.json')
    modded_trinket_buffs_filename = os.path.join(script_dir, 'mod', 'shared', 'buffs', 'base.buffs.json')
    modded_img_dir = os.path.join(script_dir, 'mod', 'panels', 'icons_equip', 'trinket')
    modded_stringtable_filename = os.path.join(script_dir, 'mod', 'localization', 'trinket_strings_table.xml')


    gen_trinket_name = generate_trinket_name(vanilla_trinkets_filepath)
    print ('trinket name ->', gen_trinket_name)

    gen_trinket_class = generate_trinket_class(trinket_properties_filepath, gen_trinket_name)
    print ('trinket class ->', gen_trinket_class)

    gen_trinket_rarity = generate_trinket_rarity(trinket_properties_filepath, gen_trinket_name)
    print ('trinket rarity ->', gen_trinket_rarity)

    gen_trinket_stats = generate_trinket_stats(trinket_effects_filepath, gen_trinket_name, gen_trinket_rarity, gen_trinket_class)
    print ('trinket stats ->', gen_trinket_stats)

    generate_trinket_entry(gen_trinket_name, modded_stringtable_filename, modded_stringtable_filename)

    buff_names = parse_gen_trinket_buffs(gen_trinket_stats, gen_trinket_name, effect_types_json_filename, modded_trinket_buffs_filename)

    parse_gen_trinket_entry(gen_trinket_name, gen_trinket_class, gen_trinket_rarity, buff_names, modded_trinket_entries_filename, trinket_properties_filepath)

    generate_image(gen_trinket_name, model_filename, modded_img_dir)