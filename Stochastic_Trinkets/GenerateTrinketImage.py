import os
import json
from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler
from scipy.ndimage import gaussian_filter
import numpy as np
from PIL import Image
import cv2

class TrinketImageGenerator:
    """
    A class for generating trinket images using Stable Diffusion.

    This class handles the process of generating, processing, and saving
    trinket images for use in a game or application.
    """

    def __init__(self, config_path):
        """
        Initialize the TrinketImageGenerator.

        Args:
            config_path (str): Path to the configuration file.
        """
        self.config = self._load_config(config_path)
        self.model_path = self._get_model_path()
        self.save_dir = self._get_save_dir()
        self.pipe = None

    def _load_config(self, config_path):
        """
        Load the configuration file.

        Args:
            config_path (str): Path to the configuration file.

        Returns:
            dict: Loaded configuration data.
        """
        with open(config_path, 'r') as f:
            return json.load(f)

    def _get_model_path(self):
        """
        Get the path to the Stable Diffusion model.

        Returns:
            str: Absolute path to the model file.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        relative_path = self.config['file_paths']['mod_resources']['T2I_checkpoint']
        return os.path.join(script_dir, relative_path)

    def _get_save_dir(self):
        """
        Get the directory path for saving generated images.

        Returns:
            str: Absolute path to the save directory.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        relative_path = self.config['file_paths']['mod_output']['mod_output_trinket_images']
        return os.path.join(script_dir, relative_path)

    def generate_image(self, trinket_name):
        """
        Generate a trinket image based on the given name.

        This method handles the entire process of image generation,
        including pipeline initialization, image creation, background
        removal, resizing, and saving.

        Args:
            trinket_name (str): Name of the trinket to generate an image for.
        """
        if not self.pipe:
            self._initialize_pipeline()

        prompt = f"{trinket_name}, 2D icon, Darkest Dungeon."
        image = self.pipe(
            prompt,
            num_inference_steps=30,
            height=768,
            width=512,
            guidance_scale=7.5,
            safety_checker=None
        ).images[0]

        image_rgba = image.convert('RGBA')
        image_no_bg = self._remove_background(image_rgba)
        image_downsized = self._resize_and_crop(image_no_bg, 72, 144)
        
        self._save_image(image_downsized, trinket_name)

    def _initialize_pipeline(self):
        """
        Initialize the Stable Diffusion pipeline.

        This method sets up the model and scheduler for image generation.
        """
        try:
            self.pipe = StableDiffusionPipeline.from_single_file(self.model_path)
            self.pipe.to("cuda")
            scheduler = EulerDiscreteScheduler(beta_start=0.00085, beta_end=0.012, beta_schedule="scaled_linear")
            self.pipe.scheduler = scheduler
        except OSError as e:
            print(f"Error loading Stable Diffusion model: {e}")
            print("Skipping image generation.")
            raise

    @staticmethod
    def _remove_background(image, tolerance=15, blur_radius=3):
        """
        Remove the background from an image with increased sensitivity.

        Args:
            image (PIL.Image): Input image with background.
            tolerance (int): Color difference tolerance for background detection.
            blur_radius (int): Radius for Gaussian blur applied to the mask.

        Returns:
            PIL.Image: Image with transparent background.
        """
        data = np.array(image)
        edges = np.concatenate([data[0, :], data[-1, :], data[:, 0], data[:, -1]])
        med_color = np.median(edges[:, :3], axis=0)
        distances = np.sqrt(np.sum((data[:,:,:3] - med_color)**2, axis=2))
        mask = distances > tolerance
        mask = gaussian_filter(mask.astype(float), sigma=blur_radius)
        mask = (mask - mask.min()) / (mask.max() - mask.min())
        data[:, :, 3] = (mask * 255).astype(np.uint8)
        
        # Apply more aggressive thresholding to remove residual background
        alpha_threshold = 180  # Lowered from 200 to remove more background
        data[:, :, 3] = np.where(data[:, :, 3] > alpha_threshold, 255, 0)
        
        # Additional step to remove isolated pixels
        kernel = np.ones((3, 3), np.uint8)
        alpha_channel = data[:, :, 3]
        alpha_channel = cv2.morphologyEx(alpha_channel, cv2.MORPH_OPEN, kernel, iterations=1)
        data[:, :, 3] = alpha_channel
        
        return Image.fromarray(data, mode='RGBA')

    @staticmethod
    def _resize_and_crop(image, target_width, target_height):
        """
        Resize and crop an image to the target dimensions.

        Args:
            image (PIL.Image): Input image to resize and crop.
            target_width (int): Desired width of the output image.
            target_height (int): Desired height of the output image.

        Returns:
            PIL.Image: Resized and cropped image.
        """
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
        return resized_image.crop((left, top, right, bottom))

    def _save_image(self, image, trinket_name):
        """
        Save the generated trinket image.

        Args:
            image (PIL.Image): Processed trinket image to save.
            trinket_name (str): Name of the trinket for file naming.
        """
        sanitized_name = trinket_name.replace(" ", "_").replace("'", "").lower()
        img_name = f"inv_trinket+{sanitized_name}.png"
        image.save(os.path.join(self.save_dir, img_name), format='PNG')

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")

    generator = TrinketImageGenerator(config_path)
    generator.generate_image("Echopearl")