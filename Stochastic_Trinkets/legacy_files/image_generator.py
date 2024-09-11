import os
from diffusers import StableDiffusionPipeline, DDPMScheduler, EulerDiscreteScheduler
from scipy.ndimage import gaussian_filter
import numpy as np
from PIL import Image

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
    # Get the original dimensions
    original_width, original_height = image.size
    
    # Calculate the target aspect ratio
    target_aspect_ratio = target_width / target_height
    
    # Calculate the aspect ratio of the original image
    original_aspect_ratio = original_width / original_height
    
    # Determine new dimensions while maintaining aspect ratio
    if original_aspect_ratio > target_aspect_ratio:
        # Image is wider than target aspect ratio
        new_height = target_height
        new_width = int(new_height * original_aspect_ratio)
    else:
        # Image is taller than target aspect ratio
        new_width = target_width
        new_height = int(new_width / original_aspect_ratio)
    
    # Resize the image
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)
    
    # Calculate the coordinates for cropping
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    
    # Crop the image to the target dimensions
    cropped_image = resized_image.crop((left, top, right, bottom))
    
    return cropped_image

def generate_image(img_name, SD_modelpath, save_dir):
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
    ).images[0]
    
    # Convert to RGBA before background removal
    image_rgba = image.convert('RGBA')
    image_no_bg = remove_background(image_rgba)

    image_downsized = resize_and_crop(image_no_bg, 72, 144)
    
    img_name = f"inv_trinket+{img_name.replace(' ', '_').lower()}.png"
    image_downsized.save(os.path.join(save_dir, img_name), format='PNG')

    
if __name__ == "__main__":

    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_filename = img_filename = os.path.join(script_dir, "fantassifiedIcons_fantassifiedIconsV20.safetensors")
    img_filename = os.path.join(script_dir, "sd_fantassified_icons_2.png")
    img_dir = os.path.join(script_dir, "modded_trinket_images")
    
    trinket_name = "test_image"

    generate_image(trinket_name, model_filename, img_dir)