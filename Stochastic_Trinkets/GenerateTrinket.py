import os
import json
from GenerateTrinketProperties import TrinketDataLoader, AIModelManager, TrinketPropertyGenerator, TrinketFactory
from ParseTrinketFiles import ConfigManager, EffectTypeManager, TrinketProcessor, StringFileManager
from GenerateTrinketImage import TrinketImageGenerator

class TrinketGenerator:
    """
    A class to generate trinkets with various properties and process them.

    This class orchestrates the trinket generation process, including creating
    trinket properties, processing buffs, generating string files, and creating
    trinket images.
    """

    def __init__(self, config_path):
        """
        Initialize the TrinketGenerator with necessary components.

        Args:
            config_path (str): Path to the configuration file.
        """
        self.config_manager = ConfigManager(config_path)
        self.effect_type_manager = EffectTypeManager(self.config_manager)
        self.trinket_processor = TrinketProcessor(self.config_manager, self.effect_type_manager)
        self.string_file_manager = StringFileManager(self.config_manager)
        self.image_generator = TrinketImageGenerator(config_path)

        self.data_loader = TrinketDataLoader(config_path)
        self.ai_manager = AIModelManager(self.data_loader.ollama_settings)
        self.property_generator = TrinketPropertyGenerator(self.data_loader, self.ai_manager)
        self.trinket_factory = TrinketFactory(self.data_loader, self.property_generator)

    def generate_trinket(self):
        """
        Generate a complete trinket with properties, buffs, and image.

        This method creates trinket properties, generates string files,
        processes trinket buffs and entries, and creates a trinket image.

        Returns:
            dict: A dictionary containing the generated trinket properties.
        """
        trinket_properties = self.trinket_factory.create_trinket()
        
        trinket_id = trinket_properties['name'].replace(" ", "_").replace("'", "").lower()
        self.string_file_manager.generate_string_file(f"str_inventory_title_trinket{trinket_id}", trinket_properties['name'])

        buff_names = self.trinket_processor.parse_gen_trinket_buffs(
            json.dumps(trinket_properties['stats']), 
            trinket_properties['name']
        )
        self.trinket_processor.parse_gen_trinket_entry(
            trinket_properties['name'],
            trinket_properties['class'],
            trinket_properties['rarity'],
            buff_names
        )

        self.image_generator.generate_image(trinket_properties['name'])

        return trinket_properties

def main():
    """
    Main function to demonstrate trinket generation.

    This function sets up the TrinketGenerator with the config file
    and generates a trinket, printing the result.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    
    trinket_generator = TrinketGenerator(config_path)
    generated_trinket = trinket_generator.generate_trinket()
    
    print("Generated Trinket:")
    print(json.dumps(generated_trinket, indent=2))

if __name__ == "__main__":
    main()