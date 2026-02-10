import torch
from diffusers import FluxPipeline
import os
import json

import argparse

# 1. SETUP PIPELINE
parser = argparse.ArgumentParser()
parser.add_argument("--outdir", type=str, help="Directory for JSON and output images")
args = parser.parse_args()

# Determine paths
if args.outdir:
    json_path = os.path.join(args.outdir, "carousal.json")
    output_dir = args.outdir
else:
    json_path = "/nuvodata/User_data/shiva/Market_carousal/carousal.json"
    output_dir = "/nuvodata/User_data/shiva/Market_carousal/flux_assets"

# Initialize Flux
pipe = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-dev",
    torch_dtype=torch.float16
).to("cuda:0") # Using GPU 0 since GPU 5 might be unavailable or as per request

pipe.load_lora_weights(
    "pictgencustomer/Carousel_127",
    weight_name="lora.safetensors"
)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

with open(json_path, 'r') as f:
    slides_data = json.load(f)

print(f"🚀 Starting dynamic generation for {len(slides_data)} slides...")

# 3. GENERATION LOOP
for slide in slides_data:
    slide_num = slide['slide_number']
    prompt_text = slide['image_prompt']
    
    # We save as slide_1.png, slide_2.png, etc.
    file_name = f"slide_{slide_num}.png"
    save_path = os.path.join(output_dir, file_name)
    
    print(f"🎨 Generating image for Slide {slide_num}...")
    
    # Enrich prompt to force clean backgrounds
    # Flux is instruction-following, so we add explicit constraints
    final_prompt = f"{prompt_text} --no text --no letters --no words --no logo --no watermark. minimalist, abstract, high quality, 8k."
    
    # Using your specific parameters
    image = pipe(
        prompt=final_prompt,
        height=1024,
        width=1024,
        guidance_scale=3.5,
        num_inference_steps=18 
    ).images[0]
    
    image.save(save_path)
    print(f"✅ Saved to {save_path}")

    # Optional: Clear VRAM cache between generations to prevent OOM
    torch.cuda.empty_cache()

print("\n✨ All assets generated from carousal.json are ready.")