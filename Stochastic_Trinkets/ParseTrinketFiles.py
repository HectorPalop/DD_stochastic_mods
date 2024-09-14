import json
import os
import ast
import re
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import shutil  # Add this import at the top of the file

class ConfigManager:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path):
        with open(config_path, 'r') as config_file:
            return json.load(config_file)

    def get_file_path(self, category, file_name):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                            self.config['file_paths'][category][file_name])

class EffectTypeManager:
    def __init__(self, config_manager):
        self.effect_types = self._load_effect_types(config_manager)

    def _load_effect_types(self, config_manager):
        effect_types_path = config_manager.get_file_path('mod_resources', 'effect_types_json')
        with open(effect_types_path, 'r') as file:
            return json.load(file)

    def get_effect_entry(self, effect_name, detail_key):
        if effect_name in self.effect_types:
            effect_details = self.effect_types[effect_name]
            if effect_details and len(effect_details) > 0:
                if detail_key in effect_details[0]:
                    return effect_details[0][detail_key]
        return None

class TrinketProcessor:
    def __init__(self, config_manager, effect_type_manager):
        self.config_manager = config_manager
        self.effect_type_manager = effect_type_manager

    def parse_gen_trinket_buffs(self, LLM_buffs_dict_string, LLM_trinket_name):
        modded_json_filepath = self.config_manager.get_file_path('mod_output', 'mod_output_trinket_buffs')
        buff_list = []
        LLM_buffs_dict = ast.literal_eval(LLM_buffs_dict_string)
        
        for i, (LLM_buff, value) in enumerate(LLM_buffs_dict.items(), 1):
            buff = self._create_buff(LLM_buff, value, LLM_trinket_name, i)
            buff_list.append(buff)
            
            if LLM_buff == 'Damage':
                buff2 = buff.copy()
                buff2['id'] = f"TRINKET_{LLM_trinket_name.replace(' ', '_').replace("'", '').lower()}_BUFF{i+1}"
                buff2['stat_sub_type'] = "damage_high"
                buff_list.append(buff2)

        self._append_entries_to_json(buff_list, modded_json_filepath, "buffs")
        return [e["id"] for e in buff_list]

    def _create_buff(self, LLM_buff, value, LLM_trinket_name, index):
        buff = {
            'id': f"TRINKET_{LLM_trinket_name.replace(' ', '_')}_BUFF{index}",
            'stat_type': self.effect_type_manager.get_effect_entry(LLM_buff, 'stat_type'),
            'stat_sub_type': "damage_low" if LLM_buff == 'Damage' else self.effect_type_manager.get_effect_entry(LLM_buff, 'stat_subtype'),
            'amount': self._calculate_amount(LLM_buff, value),
            'remove_if_not_active': False,
            'rule_type': "always",
            'is_false_rule': False,
            'rule_data': {"float": 0, "string": ""}
        }
        return buff

    def _calculate_amount(self, LLM_buff, value):
        magnitude_type = self.effect_type_manager.get_effect_entry(LLM_buff, 'magnitude_type')
        
        # Handle the case where value is '-'
        if value == '-':
            return 0  # or any other default value that makes sense for your use case
        
        # Remove any '+' or '-' signs from the value string
        value = value.lstrip('+-')
        
        try:
            amount = float(value) / 100 if magnitude_type == "percent" else float(value)
        except ValueError:
            print(f"Warning: Invalid value '{value}' for buff '{LLM_buff}'. Using 0 as default.")
            return 0  # or any other default value that makes sense for your use case
        
        return -amount if LLM_buff == 'Death Blow' else amount

    def _append_entries_to_json(self, new_entries, filename, type):
        data = {type: []}
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                with open(filename, 'r') as file:
                    data = json.load(file)
            except json.JSONDecodeError:
                print(f"Error reading {filename}. File might be corrupted. Starting with empty {type} list.")
        
        if type in data:
            data[type].extend(new_entries)
        else:
            data[type] = new_entries
        
        with open(filename, 'w') as file:
            json.dump(data, file, indent=3)

    def parse_gen_trinket_entry(self, trinket_name, trinket_class, trinket_rarity, trinket_buffs):
        modded_entries_filepath = self.config_manager.get_file_path('mod_output', 'mod_output_trinket_entries')
        trinket_properties_filepath = self.config_manager.get_file_path('mod_resources', 'trinket_properties_json')
        
        with open(trinket_properties_filepath, 'r') as file:
            properties = json.load(file)
        
        rarities_dict = properties["rarity"]
        
        # Check if the rarity exists in vanilla rarities
        try:
            vanilla_rarities_path = self.config_manager.get_file_path('mod_resources', 'vanilla_rarities_trinkets_json')
            with open(vanilla_rarities_path, 'r') as file:
                vanilla_rarities = json.load(file)
            
            if not any(rarity['id'] == trinket_rarity for rarity in vanilla_rarities['rarities']):
                self._add_new_rarity(trinket_rarity)
                self._add_rarity_string(trinket_rarity)
        except (KeyError, FileNotFoundError):
            # If the vanilla rarities file is not specified or not found, always add the new rarity
            self._add_new_rarity(trinket_rarity)
            self._add_rarity_string(trinket_rarity)
        
        # Handle the "stochastic" rarity image
        if trinket_rarity.lower() == "stochastic":
            self._copy_stochastic_rarity_image()
        
        trinket_entry = {
            "id": trinket_name.replace(" ", "_").replace("'", "").lower(),
            "buffs": trinket_buffs,
            "hero_class_requirements": [] if trinket_class == 'every_class' else [trinket_class],
            "rarity": trinket_rarity,
            "price": rarities_dict[trinket_rarity],
            "limit": 1,
            "origin_dungeon": ""
        }
        
        self._append_entries_to_json([trinket_entry], modded_entries_filepath, "entries")

    def _add_new_rarity(self, rarity):
        modded_rarities_path = self.config_manager.get_file_path('mod_output', 'mod_output_trinket_rarities')
        rarity_id = rarity.replace(" ", "_").lower()
        new_rarity = {
            "id": rarity_id,
            "award_category": "universal"
        }
        
        if os.path.exists(modded_rarities_path) and os.path.getsize(modded_rarities_path) > 0:
            with open(modded_rarities_path, 'r') as file:
                modded_rarities = json.load(file)
        else:
            modded_rarities = {"rarities": []}
        
        if not any(r['id'] == rarity_id for r in modded_rarities['rarities']):
            modded_rarities['rarities'].append(new_rarity)
        
        with open(modded_rarities_path, 'w') as file:
            json.dump(modded_rarities, file, indent=3)

    def _add_rarity_string(self, rarity):
        string_file_manager = StringFileManager(self.config_manager)
        rarity_id = rarity.replace(" ", "_").lower()
        string_file_manager.generate_string_file(f"trinket_rarity_{rarity_id}", rarity, is_rarity=True)

    def _copy_stochastic_rarity_image(self):
        source_path = self.config_manager.get_file_path('mod_resources', 'iridescent_frame')
        destination_folder = self.config_manager.get_file_path('mod_output', 'mod_output_trinket_images')
        destination_path = os.path.join(destination_folder, "rarity_stochastic.png")

        # Create the destination folder if it doesn't exist
        os.makedirs(destination_folder, exist_ok=True)

        # Copy the file
        shutil.copy2(source_path, destination_path)
        print(f"Copied stochastic rarity image to: {destination_path}")

class StringFileManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def generate_string_file(self, entry_id, entry_text, is_rarity=False):
        output_file_path = self.config_manager.get_file_path('mod_output', 'mod_output_string_table')
        
        if not os.path.exists(output_file_path) or os.path.getsize(output_file_path) == 0:
            root = self._create_new_xml_structure()
        else:
            root = self._parse_existing_xml(output_file_path)

        # Check if the entry already exists
        existing_entry = root.find(f".//entry[@id='{entry_id}']")
        if existing_entry is not None:
            if not is_rarity:
                # Update existing non-rarity entry
                existing_entry.text = entry_text
            return  # Don't add duplicate entries, especially for rarities

        new_entry = ET.Element("entry", id=entry_id)
        new_entry.text = entry_text

        for language in root.findall('language'):
            language.append(new_entry)

        self._write_xml_to_file(root, output_file_path)

    def _create_new_xml_structure(self):
        root = ET.Element("root")
        languages = ["english", "french", "german", "spanish", "brazilian", "russian", 
                     "polish", "czech", "italian", "schinese", "koreanb", "koreana", "japanese"]
        for lang in languages:
            ET.SubElement(root, "language", id=lang)
        return root

    def _parse_existing_xml(self, file_path):
        try:
            tree = ET.parse(file_path)
            return tree.getroot()
        except ET.ParseError:
            print(f"Error parsing {file_path}. Creating a new XML structure.")
            return self._create_new_xml_structure()

    def _write_xml_to_file(self, root, file_path):
        xml_str = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(xml_str)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        pretty_xml = re.sub(r'>\n\s+([^<>\s])', r'>\1', pretty_xml)
        pretty_xml = re.sub(r'\n\s*\n', '\n', pretty_xml)
        pretty_xml = pretty_xml.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>')
        pretty_xml = re.sub(r'<entry([^>]*)>([^<]+)</entry>', r'<entry\1><![CDATA[\2]]></entry>', pretty_xml)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    config_manager = ConfigManager(config_path)
    effect_type_manager = EffectTypeManager(config_manager)
    trinket_processor = TrinketProcessor(config_manager, effect_type_manager)
    string_file_manager = StringFileManager(config_manager)

    gen_trinket_name = "Echopearl"
    gen_trinket_class = "jester"
    gen_trinket_rarity = "uncommon"
    gen_trinket_stats = "{'Virtue Chance': '+5', 'Debuff Resist': '+15'}"  

    trinket_id = gen_trinket_name.replace(" ", "_").replace("'", "").lower()
    string_file_manager.generate_string_file(f"str_inventory_title_trinket{trinket_id}", gen_trinket_name)

    buff_names = trinket_processor.parse_gen_trinket_buffs(gen_trinket_stats, gen_trinket_name)
    trinket_processor.parse_gen_trinket_entry(gen_trinket_name, gen_trinket_class, gen_trinket_rarity, buff_names)

if __name__ == "__main__":
    main()