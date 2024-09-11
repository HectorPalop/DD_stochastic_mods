import torch
import os
from diffusers import FluxPipeline

script_dir = os.path.dirname(os.path.abspath(__file__))
img_filename = os.path.join(script_dir, "flux-schnell.png")

pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-schnell", torch_dtype=torch.bfloat16) # can replace schnell with dev
# to run on low vram GPUs (i.e. between 4 and 32 GB VRAM)
pipe.enable_sequential_cpu_offload()
pipe.vae.enable_slicing()
pipe.vae.enable_tiling()

pipe.to(torch.float16) # casting here instead of in the pipeline constructor because doing so in the constructor loads all models into CPU memory at once

prompt = "A 2D icon from the videogame Darkest Dungeon of a trinket named Book of Forbidden Knowledge."
out = pipe(
    prompt=prompt,
    guidance_scale=0.,
    height=768,
    width=512,
    num_inference_steps=4,
    max_sequence_length=256,
).images[0]
out.save(img_filename)