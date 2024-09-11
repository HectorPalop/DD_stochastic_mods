import json
import os
import ollama
import ast
import re

class TrinketDataLoader:
    """
    A class for loading and managing trinket-related data from configuration files.

    This class handles the loading of various trinket properties, including unique IDs,
    effect names, hero classes, and rarities from JSON files specified in the config.
    """

    def __init__(self, config_path):
        """
        Initialize the TrinketDataLoader with the given configuration file path.

        Args:
            config_path (str): Path to the configuration JSON file.
        """
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = self.load_config(config_path)
        self.file_paths = self.config['file_paths']['mod_resources']
        self.ollama_settings = self.config['ollama_settings']

    def load_config(self, config_path):
        """
        Load the configuration from the specified JSON file.

        Args:
            config_path (str): Path to the configuration JSON file.

        Returns:
            dict: Loaded configuration data.
        """
        with open(config_path, 'r') as config_file:
            return json.load(config_file)

    def get_unique_ids(self):
        """
        Retrieve unique trinket IDs from the vanilla trinket entries JSON file.

        Returns:
            list: A list of unique trinket IDs.
        """
        vanilla_trinkets_filepath = os.path.join(self.script_dir, self.file_paths['vanilla_trinket_entries_json'])
        with open(vanilla_trinkets_filepath, 'r') as file:
            data = json.load(file)
        return list({entry['id'] for entry in data['entries']})

    def get_effect_names(self):
        """
        Retrieve effect names from the trinket effects JSON file.

        Returns:
            list: A list of trinket effect names.
        """
        trinket_effects_filepath = os.path.join(self.script_dir, self.file_paths['trinket_effects_json'])
        with open(trinket_effects_filepath, 'r') as file:
            json_data = json.load(file)
        return [effect['name'] for effect in json_data['effects'] if 'name' in effect]

    def get_hero_classes(self):
        """
        Retrieve hero class requirements from the trinket properties JSON file.

        Returns:
            list: A list of hero classes that can use trinkets.
        """
        trinket_properties_filepath = os.path.join(self.script_dir, self.file_paths['trinket_properties_json'])
        with open(trinket_properties_filepath, 'r') as file:
            properties = json.load(file)
        return properties["hero_class_requirements"]

    def get_trinket_rarities(self):
        """
        Retrieve trinket rarity categories from the trinket properties JSON file.

        Returns:
            list: A list of trinket rarity categories.
        """
        trinket_properties_filepath = os.path.join(self.script_dir, self.file_paths['trinket_properties_json'])
        with open(trinket_properties_filepath, 'r') as file:
            properties = json.load(file)
        return list(properties["rarity"].keys())

    def load_json_to_string(self, filename):
        """
        Load a JSON file and convert it to a formatted string.

        Args:
            filename (str): The key for the file path in self.file_paths.

        Returns:
            str: A formatted JSON string with spaces after commas and colons.
        """
        full_path = os.path.join(self.script_dir, self.file_paths[filename])
        with open(full_path, 'r') as file:
            data = json.load(file)
        json_string = json.dumps(data, separators=(',', ':'))
        return re.sub(r'([,:])(?![\d\s])', r'\1 ', json_string)

class AIModelManager:
    """
    A class for managing AI model interactions using Ollama.

    This class handles the creation of system prompts and generation of responses
    using specified AI models and settings.
    """

    def __init__(self, ollama_settings):
        """
        Initialize the AIModelManager with the given Ollama settings.

        Args:
            ollama_settings (dict): A dictionary containing Ollama model settings.
        """
        self.ollama_settings = ollama_settings

    def create_system_prompt(self, model_name, header, content):
        """
        Create a system prompt for the specified model.

        Args:
            model_name (str): The name of the model to use.
            header (str): The header text for the system prompt.
            content (str): The content to include in the system prompt.

        Returns:
            str: A formatted system prompt string.
        """
        model = self.ollama_settings[model_name]['model']
        temperature = self.ollama_settings[model_name]['temperature']
        from_line = f"FROM {model}"
        parameter_line = f"PARAMETER temperature {temperature}"
        return f"{from_line}\n{parameter_line}\n{header}{content}".strip()

    def generate_response(self, model_name, system_prompt, user_content):
        """
        Generate a response using the specified model and system prompt.

        Args:
            model_name (str): The name of the model to use.
            system_prompt (str): The system prompt to use for the model.
            user_content (str): The user's input content.

        Returns:
            str: The generated response from the AI model.
        """
        model = self.ollama_settings[model_name]['model']
        ollama.create(model=model_name, modelfile=system_prompt)
        print(f'{model_name} model loaded')
        response = ollama.chat(model=model_name, keep_alive=0, messages=[
            {'role': 'user', 'content': user_content},
        ])
        return response['message']['content']

class TrinketPropertyGenerator:
    """
    A class for generating various properties of trinkets using AI models.

    This class uses the TrinketDataLoader and AIModelManager to generate
    names, classes, rarities, and stats for trinkets in the game.
    """

    def __init__(self, data_loader, ai_manager):
        """
        Initialize the TrinketPropertyGenerator with data loader and AI manager.

        Args:
            data_loader (TrinketDataLoader): An instance of TrinketDataLoader.
            ai_manager (AIModelManager): An instance of AIModelManager.
        """
        self.data_loader = data_loader
        self.ai_manager = ai_manager

    def generate_name(self):
        """
        Generate a unique name for a trinket using the AI model.

        Returns:
            str: A generated trinket name.
        """
        unique_ids = self.data_loader.get_unique_ids()
        header = (
            "SYSTEM "
            "You are tasked with deciding names of gamefiles in the video game Darkest Dungeon. "
            "Answer only with ONE plausible name for the game file and NOTHING ELSE. "
            "Choose a name that is in line with the themes of the game (dark fantasy, lovecraftian). "
            "Favor darker themes, and avoid the word 'whisper'. "
            "Choose a name that is different but in the same format as any in the following list: "
        )
        system_prompt = self.ai_manager.create_system_prompt('DD_trinket_namer', header, " ".join(unique_ids))
        response = self.ai_manager.generate_response('DD_trinket_namer', system_prompt, 
            'Please suggest a unique trinket name. Avoid the word whisper. Answer only with ONE plausible name for the game file and NOTHING ELSE.')
        return response.replace('"', "")

    def generate_class(self, trinket_name):
        """
        Generate a hero class for a trinket using the AI model.

        Args:
            trinket_name (str): The name of the trinket.

        Returns:
            str: A generated hero class or 'every_class'.
        """
        hero_classes = self.data_loader.get_hero_classes()
        header = (
            f"SYSTEM "
            f"You are tasked with deciding properties of gamefiles in the video game Darkest Dungeon. "
            f"More specifically, you will be deciding the hero class (if any) of a trinket in the game, called: {trinket_name}. "
            f"If this trinket is generic and fits all classes, please just answer the word: every_class. "
            f"On the contrary, if this name particularly suits one of the following hero classes, answer with the name of the hero class. "
            f"In any case, answer only with either every_class or a class name and NOTHING ELSE. "
            f"Here is the list of all the class names in the game: "
        )
        system_prompt = self.ai_manager.create_system_prompt('DD_trinket_class_namer', header, " ".join(hero_classes))
        
        while True:
            response = self.ai_manager.generate_response('DD_trinket_class_namer', system_prompt, 
                'Please suggest the hero class for the trinket. Answer only with either every_class or a class name and NOTHING ELSE.')
            gen_name = response.replace('"', "").lower()
            if gen_name in hero_classes or gen_name == 'every_class':
                return gen_name
            print(f'Invalid class: {gen_name}')

    def generate_rarity(self, trinket_name):
        """
        Generate a rarity for a trinket using the AI model.

        Args:
            trinket_name (str): The name of the trinket.

        Returns:
            str: A generated rarity category.
        """
        trinket_rarities = self.data_loader.get_trinket_rarities()
        header = (
            f"SYSTEM "
            f"You are tasked with deciding properties of gamefiles in the video game Darkest Dungeon. "
            f"More specifically, you will be deciding the rarity of a trinket in the game, called: {trinket_name}. "
            f"Choose a rarity that fits the name of the trinket. "
            f"Answer only with the rarity of the trinket and NOTHING ELSE. "
            f"Here is the list of all the possible rarities in the game: "
        )
        system_prompt = self.ai_manager.create_system_prompt('DD_trinket_rarity_namer', header, " ".join(trinket_rarities))
        
        while True:
            response = self.ai_manager.generate_response('DD_trinket_rarity_namer', system_prompt, 
                'Please suggest the rarity category for the trinket. Answer only with a valid rarity and NOTHING ELSE.')
            gen_name = response.replace('"', "").lower()
            if gen_name in trinket_rarities:
                return gen_name

    def generate_stats(self, trinket_name, trinket_rarity, trinket_class):
        """
        Generate stats for a trinket using the AI model.

        Args:
            trinket_name (str): The name of the trinket.
            trinket_rarity (str): The rarity of the trinket.
            trinket_class (str): The hero class of the trinket.

        Returns:
            dict: A dictionary of generated stats and their values.
        """
        vanilla_stats = self.data_loader.get_effect_names()
        header = (
            f"SYSTEM "
            f"You are tasked with deciding the effects from trinkets in the video game Darkest Dungeon. "
            f"You should choose stats that are representative of the trinket's title, which is: {trinket_name}. "
            f"The rarity of the trinket is {trinket_rarity.replace('_', ' ')} and it is useable by {trinket_class.replace('_', ' ')}. "
            f"Choose a minimum of 1 and a maximum of 5 stats. Balance positive with negative effects. "
            f"Precede each stat with either a + or a - depending on whether the effect to apply should be positive or negative. "
            f"Avoid repeating stats. "
            f"Example: ['+Accuracy', '+Damage', '+Stress', '-Move Resist'] "
            f"IMPORTANT: Each stat should be one of the following list (WRITE THEM EXACTLY AS THEY APPEAR HERE): "
        )
        system_prompt = self.ai_manager.create_system_prompt('DD_trinket_stat_namer', header, " ".join(vanilla_stats))
        
        while True:
            response = self.ai_manager.generate_response('DD_trinket_stat_namer', system_prompt, 
                'Please suggest a list of trinket stats. Answer ONLY with a python list with these stats and NOTHING ELSE.')
            print(response)
            parsed_stats = self.parse_effects(response, vanilla_stats)
            if parsed_stats:
                break
        
        trinket_bounds = self.data_loader.load_json_to_string('trinket_effects_json')
        header = (
            f"SYSTEM "
            f"You are tasked with tuning the values of the effects from trinkets in the video game Darkest Dungeon. "
            f"The trinket you are currently analyzing is: {trinket_name}. "
            f"The rarity of the trinket is {trinket_rarity.replace('_', ' ')} and it is useable by {trinket_class.replace('_', ' ')}. "
            f"More rare and class-specific trinkets have more potent effects (both positive and negative), whereas common trinkets are weaker. "
            f"The user will give you a python dictionary. "
            f"The keys of the dictionary are the names of the stats from the trinket. "
            f"The values of the dictionary are + and - symbols, representing whether the stat should be positive or negative. "
            f"Your task is to replace these symbols with specific numerical values within the allowed range for each stat. "
            f"The names of the stats that you write should be exactly the same as the ones provided by the user. "
            f"For each of those stats, choose concrete numerical values, not just ranges of values. "
            f"The maximum and minimum magnitudes for each stat are given below in a json file. "
            f"EXAMPLE: "
            f"user: STATS: {{'Bleed Resist': '-', 'Healing Received': '+', 'Stress': '-'}} Please answer ONLY with the completed dictionary and NOTHING ELSE. "
            f"expected output: {{'Bleed Resist': '-10', 'Healing Received': '+30', 'Stress': '-20'}} "
            f"JSON FILE DETAILING THE MAXIMUM AND MINIMUM MAGNITUDES FOR EACH STAT: {trinket_bounds}"
        )
        system_prompt = self.ai_manager.create_system_prompt('DD_trinket_stat_tuner', header, "")
        response = self.ai_manager.generate_response('DD_trinket_stat_tuner', system_prompt, 
            f'STATS: {parsed_stats} Please answer ONLY with the completed dictionary and NOTHING ELSE.')
        
        try:
            tuned_stats = ast.literal_eval(response)
            if isinstance(tuned_stats, dict) and all(isinstance(v, (int, str)) for v in tuned_stats.values()):
                return tuned_stats
            else:
                print("Invalid response format. Using original parsed stats.")
                return parsed_stats
        except:
            print("Failed to process tuned stats. Using original parsed stats.")
            return parsed_stats

    def parse_effects(self, LLM_effects, vanilla_stats):
        """
        Parse the effects generated by the AI model.

        Args:
            LLM_effects (str): The effects string generated by the AI model.
            vanilla_stats (list): A list of valid vanilla stats.

        Returns:
            dict: A dictionary of parsed effects, or False if parsing fails.
        """
        try:
            preparsed_effects = LLM_effects.strip('[]').split(', ')
            parsed_effects = [item.strip("'") for item in preparsed_effects]
        except:
            try:
                preparsed_effects = ast.literal_eval(LLM_effects)
                parsed_effects = f"[{', '.join(preparsed_effects)}]"
            except:
                print('Incorrect python format. Re-attempting...')
                return False
        
        if not all(effect[1:].strip() in vanilla_stats for effect in parsed_effects):
            print('Some effect was not recognized. Re-attempting...')
            for effect in parsed_effects:
                if effect[1:].strip() not in vanilla_stats:
                    print("Effect not in vanilla stats:", effect[1:].strip())
            return False
        
        result_dict = {item[1:].strip(): item[0] for item in parsed_effects}
        return result_dict

class TrinketFactory:
    """
    A class for creating complete trinket objects.

    This class uses the TrinketDataLoader and TrinketPropertyGenerator
    to create fully-defined trinket objects with all necessary properties.
    """

    def __init__(self, data_loader, property_generator):
        """
        Initialize the TrinketFactory with data loader and property generator.

        Args:
            data_loader (TrinketDataLoader): An instance of TrinketDataLoader.
            property_generator (TrinketPropertyGenerator): An instance of TrinketPropertyGenerator.
        """
        self.data_loader = data_loader
        self.property_generator = property_generator

    def create_trinket(self):
        """
        Create a complete trinket object with all properties.

        This method generates a name, class, rarity, and stats for a trinket,
        combining them into a single dictionary representing the trinket.

        Returns:
            dict: A dictionary containing all properties of the generated trinket.
        """
        name = self.property_generator.generate_name()
        print('Trinket name ->', name)

        trinket_class = self.property_generator.generate_class(name)
        print('Trinket class ->', trinket_class)

        rarity = self.property_generator.generate_rarity(name)
        print('Trinket rarity ->', rarity)

        stats = self.property_generator.generate_stats(name, rarity, trinket_class)
        print('Trinket stats ->', stats)

        return {
            'name': name,
            'class': trinket_class,
            'rarity': rarity,
            'stats': stats
        }

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    data_loader = TrinketDataLoader(config_path)
    ai_manager = AIModelManager(data_loader.ollama_settings)
    property_generator = TrinketPropertyGenerator(data_loader, ai_manager)
    trinket_factory = TrinketFactory(data_loader, property_generator)

    trinket = trinket_factory.create_trinket()