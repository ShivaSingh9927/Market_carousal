import os
import sys
import json
import pandas as pd
import datetime
import logging
from io import StringIO
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
BASE_PATH = "/nuvodata/User_data/shiva/Market_carousal"
CSV_PATH = os.path.join(BASE_PATH, "marketing_plan.csv")
OUTPUT_JSON = os.path.join(BASE_PATH, "carousal.json")

# Initialize Model
model = init_chat_model("llama-3.3-70b-versatile", model_provider="groq", max_tokens=4000)

def find_column(df, target_names):
    """Fuzzy match column names to handle Llama's formatting variations."""
    cols = {c.lower().strip(): c for c in df.columns}
    for name in target_names:
        clean_name = name.lower().strip()
        if clean_name in cols:
            return cols[clean_name]
    return None

def generate_carousel_json(topic, talking_points, goal):
    prompt = f"""
    You are an expert LinkedIn Strategist for Nueralogic (AI Agency).
    Create a content package: 6-slide carousel + Social Media Captions.
    
    Data:
    - Topic: {topic}
    - Details: {talking_points}
    - Goal: {goal}
    
    RETURN JSON OBJECT ONLY (Strict JSON standard):
    - NO control characters (newlines, tabs) inside strings. Use \\n and \\t.
    - Escape all double quotes inside strings.
    - IMPORTANT: Wrap key terms in <b> tags for highlighting (e.g. "We use <b>AI Agents</b> to...").

    
    {{
        "linkedin_post": "Professional post... (use \\n for line breaks)",
        "instagram_caption": "Engaging caption...",
        "slides": [
            {{ "slide_number": 1, "title": "...", "content": "...", "image_prompt": "Create Realistic cinematic visualization to explain {topic}. Conceptual representation using [geometric shapes/flowing glass/data nodes]. Soft studio lighting, deep depth of field with bokeh, metallic and translucent textures. Professional color palette. 8k resolution, photorealistic. NO TEXT, NO LOGOS, NO SIGNS, NO WORDS." }},
            ...
        ]
    }}
    """
    
    print(f"🧠 Llama is creating content for: {topic}")
    response = model.invoke([HumanMessage(content=prompt)], temperature=0.7)
    
    content = response.content
    # Cleanup markdown
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
        
    try:
        return json.loads(content, strict=False)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON Decode Error: {e}")
        print("Attempting to repair...")
        # Fallback: Sometimes LLMs output Python dicts
        try:
            import ast
            return ast.literal_eval(content)
        except:
            # Last resort: Try to escape newlines manually if that's the issue
            try:
                fixed_content = content.replace("\n      ", "").replace("\n", "\\n")
                return json.loads(fixed_content, strict=False)
            except:
                raise e
def main():
    # --- ARGUMENT PARSING ---
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", type=str, help="Target day")
    parser.add_argument("--outdir", type=str, help="Output directory for JSON and text")
    args = parser.parse_args()

    # Determine Output Path
    if args.outdir:
        if not os.path.exists(args.outdir):
            os.makedirs(args.outdir)
        output_json_path = os.path.join(args.outdir, "carousal.json")
        captions_path = os.path.join(args.outdir, "social_captions.txt")
    else:
        output_json_path = OUTPUT_JSON
        captions_path = os.path.join(BASE_PATH, "social_captions.txt")

    try:
        if not os.path.exists(CSV_PATH):
            raise FileNotFoundError(f"CSV not found at {CSV_PATH}")

        df = pd.read_csv(CSV_PATH)
        df.columns = df.columns.str.strip()

        day_col = find_column(df, ['Day', 'Date'])
        if day_col:
            df[day_col] = df[day_col].astype(str).str.strip()

        topic_col = find_column(df, ['Topic / Subject', 'Topic', 'Subject'])
        
        # Strategies to find content
        points_col = find_column(df, ['Key Talking Points', 'Talking Points', 'Points'])
        goal_col = find_column(df, ['Goal / CTA', 'Goal', 'CTA'])
        
        # Check for Slide columns (Slide1, Slide2...)
        slide_cols = [c for c in df.columns if c.lower().startswith('slide') and c[-1].isdigit()]

        # --- SELECT ROW ---
        if args.day:
            target_day = args.day
            print(f"🎯 Pipeline requested Day: {target_day}")
            df[day_col] = df[day_col].astype(str)
            row = df[df[day_col].str.lower().str.strip() == str(target_day).lower().strip()]
        else:
            today = datetime.datetime.now().strftime("%a") 
            print(f"📅 No argument provided. Defaulting to Today: {today}")
            row = df[df[day_col].str.contains(today, case=False, na=False)]
        
        target_row = row.iloc[0] if not row.empty else df.iloc[0]

        # --- EXTRACT CONTENT ---
        talking_points = ""
        goal = "General Brand Awareness" 

        if points_col and goal_col:
            talking_points = str(target_row[points_col])
            goal = str(target_row[goal_col])
        elif slide_cols:
            slide_cols.sort()
            points_list = [f"{c}: {target_row[c]}" for c in slide_cols if pd.notna(target_row[c])]
            talking_points = "; ".join(points_list)
            if goal_col and pd.notna(target_row[goal_col]):
                goal = str(target_row[goal_col])
        else:
             raise KeyError(f"Missing required columns. Found: {list(df.columns)}")

        # --- GENERATE ---
        full_data = generate_carousel_json(
            str(target_row[topic_col]), 
            talking_points, 
            goal
        )
        
        # Extract parts
        slides = full_data.get("slides", [])
        linkedin = full_data.get("linkedin_post", "")
        instagram = full_data.get("instagram_caption", "")
        
        # Save Slides JSON
        with open(output_json_path, 'w') as f:
            json.dump(slides, f, indent=4) # Save ONLY the list for compatibility
            
        # Save Captions
        with open(captions_path, 'w') as f:
            f.write(f"--- LINKEDIN POST ---\n{linkedin}\n\n")
            f.write(f"--- INSTAGRAM CAPTION ---\n{instagram}\n")

        print(f"✅ Success: Data generated in {output_json_path}")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
if __name__ == "__main__":
    main()