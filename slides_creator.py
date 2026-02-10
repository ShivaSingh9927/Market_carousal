import cairo
import os
import json
import re
from PIL import Image, ImageFilter

# =======================
# BRAND THEME
# =======================
THEME = {
    'primary': (0.278, 0.121, 1.0),
    'accent': (0.674, 0.666, 1.0),
    'white': (1.0, 1.0, 1.0),
    'overlay': (0, 0, 0, 0.78)
}

# =======================
# RENDERER
# =======================
class Renderer:
    def __init__(self, w=1080, h=1080):
        self.w, self.h = w, h
        self.margin_x = 80
        self.safe_bottom = h - 120

    # --------------------------------------------------
    # PIXEL-SAFE TEXT ENGINE (BOLD + WRAP)
    # --------------------------------------------------
    def draw_text_engine(self, ctx, text, x, y, size, max_width_px, color, bold_color):
        ctx.set_font_size(size)

        # ---- 1. Tokenize into (word, is_bold)
        tokens = []
        parts = re.split(r'(<b>.*?</b>)', text)

        for part in parts:
            if not part:
                continue
            if part.startswith('<b>') and part.endswith('</b>'):
                content = part[3:-4]
                tokens.extend([(w, True) for w in content.split(' ')])
            else:
                tokens.extend([(w, False) for w in part.split(' ')])

        # ---- 2. Line wrapping using pixel width
        lines = []
        current_line = []
        current_width = 0

        for word, is_bold in tokens:
            word_text = word + " "
            ctx.select_font_face(
                "Sans",
                cairo.FONT_SLANT_NORMAL,
                cairo.FONT_WEIGHT_BOLD if is_bold else cairo.FONT_WEIGHT_NORMAL
            )
            word_width = ctx.text_extents(word_text).x_advance

            if current_width + word_width > max_width_px:
                lines.append(current_line)
                current_line = [(word_text, is_bold)]
                current_width = word_width
            else:
                current_line.append((word_text, is_bold))
                current_width += word_width

        if current_line:
            lines.append(current_line)

        # ---- 3. Render lines
        curr_y = y
        for line in lines:
            if curr_y > self.safe_bottom:
                break

            curr_x = x
            for segment, is_bold in line:
                ctx.select_font_face(
                    "Sans",
                    cairo.FONT_SLANT_NORMAL,
                    cairo.FONT_WEIGHT_BOLD if is_bold else cairo.FONT_WEIGHT_NORMAL
                )
                ctx.set_source_rgb(*(bold_color if is_bold else color))
                ctx.move_to(curr_x, curr_y)
                ctx.show_text(segment)
                curr_x += ctx.text_extents(segment).x_advance

            curr_y += size * 1.45

        return curr_y

    # --------------------------------------------------
    # CREATE SINGLE SLIDE
    # --------------------------------------------------
    def create_slide(self, data, out_path, bg_path):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.w, self.h)
        ctx = cairo.Context(surface)

        # ---- Background (Blurred & Dimmed)
        if os.path.exists(bg_path):
            # Blur using PIL
            pil_img = Image.open(bg_path).convert("RGB")
            # light blur only to soften noise
            pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=2)) 
            
            # Convert to Cairo-compatible format (BGRA is standard for Cairo ImageSurface)
            # But easiest way is to save to a temp buffer or file
            # Let's just overwrite a temp file or use a memory buffer
            # Actually, let's keep it simple: Save to a temp png
            temp_bg = out_path + ".temp_bg.png"
            pil_img.save(temp_bg)
            
            img = cairo.ImageSurface.create_from_png(temp_bg)
            scale = max(self.w / img.get_width(), self.h / img.get_height())
            ctx.save()
            ctx.scale(scale, scale)
            ctx.set_source_surface(img, 0, 0)
            ctx.paint()
            ctx.restore()
            
            # remove temp file
            if os.path.exists(temp_bg):
                os.remove(temp_bg)

        # ---- Overlay (Darkened for readability)
        # Signficantly reduced opacity to make images visible
        ctx.set_source_rgba(0, 0, 0, 0.40) 
        ctx.rectangle(0, 0, self.w, self.h)
        ctx.fill()

        # ---- Accent strip
        ctx.set_source_rgb(*THEME['accent'])
        ctx.rectangle(0, 0, 15, self.h)
        ctx.fill()

        # ---- Branding
        ctx.set_source_rgb(*THEME['accent'])
        ctx.set_font_size(32)
        ctx.move_to(self.margin_x, 100)
        ctx.show_text("NUERALOGIC")

        # ---- Title
        y_after_title = self.draw_text_engine(
            ctx,
            data.get("title", ""),
            self.margin_x,
            250,
            75,
            self.w - self.margin_x * 2,
            THEME['white'],
            THEME['white']
        )

        # ---- Content
        self.draw_text_engine(
            ctx,
            data.get("content", ""),
            self.margin_x,
            y_after_title + 80,
            40,
            self.w - self.margin_x * 2,
            THEME['white'],
            THEME['accent']
        )

        # ---- Footer
        ctx.set_source_rgb(*THEME['accent'])
        ctx.set_font_size(28)
        ctx.move_to(self.margin_x, 1020)
        ctx.show_text("nueralogic.com")

        if 'slide_number' in data:
            ctx.move_to(980, 1020)
            ctx.show_text(f"{data['slide_number']:02d}")

        surface.write_to_png(out_path)

# =======================
# PIPELINE RUNNER
# =======================
# =======================
# PIPELINE RUNNER
# =======================
def run_render():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=str, help="Output folder")
    args = parser.parse_args()

    BASE = "/nuvodata/User_data/shiva/Market_carousal"
    
    if args.outdir:
        OUT_DIR = args.outdir
        # Images are also in OUT_DIR
        FLUX_DIR = args.outdir
        JSON_FILE = os.path.join(OUT_DIR, "carousal.json")
    else:
        OUT_DIR = os.path.join(BASE, "output_slides")
        FLUX_DIR = os.path.join(BASE, "flux_assets")
        JSON_FILE = os.path.join(BASE, "carousal.json")

    os.makedirs(OUT_DIR, exist_ok=True)

    with open(JSON_FILE, "r") as f:
        slides = json.load(f)

    renderer = Renderer()
    pngs = []
    
    print(f"🎨 Rendering {len(slides)} slides from {FLUX_DIR} to {OUT_DIR}")

    for s in slides:
        num = s["slide_number"]
        out = os.path.join(OUT_DIR, f"final_slide_{num:02d}.png")
        # Ensure filename match with flux output
        # Flux outputs: slide_1.png (no leading zero) or slide_01.png?
        # Image creator said: f"slide_{slide_num}.png"
        bg = os.path.join(FLUX_DIR, f"slide_{num}.png")
        
        if not os.path.exists(bg):
            print(f"⚠️ Warning: BG not found: {bg}")
            continue
            
        renderer.create_slide(s, out, bg)
        pngs.append(out)

    # ---- Export PDF
    if pngs:
        images = [Image.open(p).convert("RGB") for p in sorted(pngs)]
        images[0].save(
            os.path.join(OUT_DIR, "Nueralogic_Carousel.pdf"),
            save_all=True,
            append_images=images[1:]
        )
        print("💎 FINAL PDF GENERATED SUCCESSFULLY")

# =======================
# ENTRY
# =======================
if __name__ == "__main__":
    run_render()
