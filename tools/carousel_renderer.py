import torch
from diffusers import FluxPipeline
import cairo
import os
import json
import re
import uuid
from PIL import Image
from langchain_core.tools import tool

# =======================
# BRAND THEME
# =======================
THEME = {
    'primary': (0.278, 0.121, 1.0),
    'accent': (0.674, 0.666, 1.0),
    'white': (1.0, 1.0, 1.0),
    'overlay': (0, 0, 0, 0.40) 
}

class Renderer:
    def __init__(self, w=1080, h=1350):
        self.w, self.h = w, h
        self.margin_x = 80
        self.safe_bottom = h - 80

    def draw_text_engine(self, ctx, text, x, y, size, max_width_px, color, highlight_color, is_title=True):
        ctx.set_font_size(size)
        
        font_extents = ctx.font_extents() 
        ascent, descent = font_extents[0], font_extents[1]
        uniform_h = ascent + descent + 10 
        
        tokens = []
        text = str(text)
        parts = re.split(r'(<b>.*?</b>)', text)
        for part in parts:
            if not part: continue
            if part.startswith('<b>') and part.endswith('</b>'):
                content = part[3:-4]
                tokens.extend([(w, True) for w in content.split(' ')])
            else:
                tokens.extend([(w, False) for w in part.split(' ')])

        curr_y = y
        curr_x = x
        line_spacing = size * 1.3

        for word, is_bold in tokens:
            word_text = word + " "
            weight = cairo.FONT_WEIGHT_BOLD if is_bold else cairo.FONT_WEIGHT_NORMAL
            ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, weight)
            
            extents = ctx.text_extents(word_text)
            
            if curr_x + extents.x_advance > x + max_width_px:
                curr_x = x
                curr_y += line_spacing

            if is_bold and not is_title:
                # Body Highlight Logic
                padding_x, padding_y = 12, 6
                ctx.save()
                ctx.set_source_rgb(*highlight_color)
                
                rect_x, rect_y = curr_x - 4, curr_y - ascent - 4
                rect_w, rect_h = extents.x_advance + 2, uniform_h
                
                ctx.rectangle(rect_x, rect_y, rect_w, rect_h)
                ctx.fill()
                ctx.restore()
                
                ctx.set_source_rgb(*color)
                ctx.move_to(curr_x, curr_y)
                ctx.show_text(word_text)
            else:
                # Title or Normal Text
                ctx.set_source_rgb(*color)
                ctx.move_to(curr_x, curr_y)
                ctx.show_text(word_text)

            curr_x += extents.x_advance
        return curr_y

    def create_slide(self, data, out_path, bg_path, slide_index):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.w, self.h)
        ctx = cairo.Context(surface)
        
        # 1. Background
        if os.path.exists(bg_path):
            img = cairo.ImageSurface.create_from_png(bg_path)
            scale = max(self.w / img.get_width(), self.h / img.get_height())
            ctx.save()
            ctx.scale(scale, scale)
            ctx.set_source_surface(img, 0, 0)
            ctx.paint()
            ctx.restore()

        # 2. Gradient Scrim (Darkens left side for text readability)
        scrim = cairo.LinearGradient(0, 0, self.w * 0.9, 0)
        scrim.add_color_stop_rgba(0, 0, 0, 0, 0.8)
        scrim.add_color_stop_rgba(0.3, 0, 0, 0, 0.3)
        ctx.set_source(scrim)
        ctx.rectangle(0, 0, self.w, self.h)
        ctx.fill()

        # 3. Logo Branding
        logo_path = "/nuvodata/User_data/shiva/Market_carousal/android-chrome-192x192.png"
        if os.path.exists(logo_path):
            logo_img = cairo.ImageSurface.create_from_png(logo_path)
            l_scale = 60 / logo_img.get_width()
            ctx.save()
            ctx.translate(self.margin_x, 80)
            ctx.scale(l_scale, l_scale)
            ctx.set_source_surface(logo_img, 0, 0)
            ctx.paint()
            ctx.restore()

        ctx.set_source_rgb(*THEME['accent'])
        ctx.set_font_size(36)
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.move_to(self.margin_x + 75, 125)
        ctx.show_text("NUERALOGIC")

        # 4. Text Content
        title = data.get("topic", "")
        content = data.get("content", "")

        y_next = self.draw_text_engine(ctx, title, self.margin_x, 350, 80, self.w*0.8, THEME['white'], THEME['white'], is_title=True)
        self.draw_text_engine(ctx, content, self.margin_x, y_next + 120, 42, self.w*0.7, THEME['white'], THEME['accent'], is_title=False)
        
        # 5. Footer
        ctx.set_source_rgba(1, 1, 1, 0.5)
        ctx.set_font_size(24)
        ctx.move_to(self.margin_x, 1310)
        ctx.show_text("nueralogic.com")
        ctx.move_to(970, 1310)
        ctx.show_text(f"{slide_index:02d}")
        
        surface.write_to_png(out_path)

@tool
def generate_and_render_carousel():
    """
    Generates a unique batch UUID, runs the Flux image pipeline on CUDA:4, 
    renders Cairo overlays, and saves a PDF.
    """
    batch_id = str(uuid.uuid4())[:8]
    BASE = "/nuvodata/User_data/shiva/Market_carousal"
    JSON_FILE = os.path.join(BASE, "final_plan.json")
    OUT_DIR = os.path.join(BASE, "output_slides", batch_id)
    FLUX_DIR = os.path.join(BASE, "flux_assets", batch_id)

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FLUX_DIR, exist_ok=True)

    if not os.path.exists(JSON_FILE):
        return "Error: final_plan.json not found."

    with open(JSON_FILE, 'r') as f:
        slides = json.load(f).get("slides", [])

    # --- PHASE 1: FLUX ---
    pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.float16).to("cuda:4")
    pipe.load_lora_weights("pictgencustomer/Carousel_127", weight_name="lora.safetensors")

    for i, s in enumerate(slides, 1):
        prompt = f"{s.get('image_prompt')} Minimalist background, clean composition, no text, no letters, no words, no signatures, no typography, cinematic lighting, 8k resolution."
        bg_path = os.path.join(FLUX_DIR, f"bg_{i}.png")
        image = pipe(prompt=prompt, height=1024, width=1024, guidance_scale=5.5, num_inference_steps=20).images[0]
        image.save(bg_path)
    
    del pipe
    torch.cuda.empty_cache()

    # --- PHASE 2: CAIRO ---
    renderer = Renderer()
    png_paths = []
    for i, s in enumerate(slides, 1):
        out_p = os.path.join(OUT_DIR, f"slide_{i:02d}.png")
        bg_p = os.path.join(FLUX_DIR, f"bg_{i}.png")
        renderer.create_slide(s, out_p, bg_p, i)
        png_paths.append(out_p)

    # --- PHASE 3: PDF ---
    pdf_path = os.path.join(OUT_DIR, f"Nueralogic_{batch_id}.pdf")
    imgs = [Image.open(p).convert("RGB") for p in sorted(png_paths)]
    imgs[0].save(pdf_path, save_all=True, append_images=imgs[1:])

    return f"SUCCESS|{pdf_path}|{OUT_DIR}"