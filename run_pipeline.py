import sys
import os
import subprocess
import time
import pandas as pd
import shutil

# --- CONFIGURATION ---
BASE_PATH = "/nuvodata/User_data/shiva/Market_carousal"
SCRIPTS = {
    "agent": f"{BASE_PATH}/content_for_slides.py",
    "flux": f"{BASE_PATH}/image_creator.py",
    "render": f"{BASE_PATH}/slides_creator.py"
}

# Directories
FLUX_ASSETS = os.path.join(BASE_PATH, "flux_assets")
OUTPUT_DIR = os.path.join(BASE_PATH, "output_slides")

# Ensure required directories exist
for folder in [FLUX_ASSETS, OUTPUT_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

def run_step(name, script_path, args=None):
    print(f"\n{'='*30}")
    print(f"▶️  STARTING STEP: {name.upper()}")
    print(f"{'='*30}")
    
    start_time = time.time()
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    # Run the command and capture output for the bot logs
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        elapsed = time.time() - start_time
        print(f"✅ {name.upper()} COMPLETED in {elapsed:.2f}s")
        return True
    else:
        print(f"❌ {name.upper()} FAILED with exit code {result.returncode}. Aborting batch.")
        return False

def main(day_filter=None):
    print("🚀 NUERALOGIC BATCH PIPELINE INITIALIZED")
    
    csv_file = os.path.join(BASE_PATH, "marketing_plan.csv")
    if not os.path.exists(csv_file):
        print(f"❌ CSV not found at {csv_file}! Run the planner first.")
        return

    try:
        df = pd.read_csv(csv_file)
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    # Identify the 'Day' column
    day_col = next((c for c in df.columns if 'day' in c.lower()), df.columns[0])
    days = df[day_col].unique()
    
    generated_files = []

    # If the bot sends a specific day, filter the list
    if day_filter:
        print(f"🎯 Targeted Mode: Processing Day {day_filter}")
        days = [d for d in days if str(d).strip().lower() == str(day_filter).strip().lower()]
        if not days:
            print(f"❌ Day '{day_filter}' not found in marketing_plan.csv!")
            return

    for day_name in days:
        print(f"\n🌟 --- PROCESSING BATCH FOR: {day_name} ---")
        
        # 1. SETUP DAY DIRECTORY
        clean_name = str(day_name).replace(" ", "_").strip()
        day_out_dir = os.path.join(OUTPUT_DIR, clean_name)
        
        os.makedirs(day_out_dir, exist_ok=True)
        print(f"📂 Output Directory: {day_out_dir}")

        # 2. RUN AGENT
        if not run_step(f"Agent ({day_name})", SCRIPTS["agent"], args=[f"--day={day_name}", f"--outdir={day_out_dir}"]):
            continue
            
        # 3. RUN FLUX
        if not run_step(f"Vision ({day_name})", SCRIPTS["flux"], args=[f"--outdir={day_out_dir}"]):
            continue
            
        # 4. RUN RENDER
        if not run_step(f"Render ({day_name})", SCRIPTS["render"], args=[f"--outdir={day_out_dir}"]):
            continue
            
        # 5. VERIFY PDF
        pdf_path = os.path.join(day_out_dir, "Nueralogic_Carousel.pdf")
        if os.path.exists(pdf_path):
            generated_files.append(pdf_path)
            print(f"📁 PDF SUCCESSFULLY GENERATED: {pdf_path}")
        else:
            print(f"⚠️ Warning: Pipeline finished but PDF missing for {day_name}")

    print("\n" + "💎" * 15)
    print(f"✅ BATCH COMPLETED. Files Generated: {len(generated_files)}")
    for f in generated_files:
        print(f" 📄 {f}")
    print("💎" * 15)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", type=str, help="Run pipeline for a specific day only")
    args = parser.parse_args()
    
    main(day_filter=args.day)