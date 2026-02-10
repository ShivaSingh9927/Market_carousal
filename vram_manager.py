# Location: /nuvodata/User_data/shiva/Market_carousal/vram_manager.py
import torch
import gc

def purge():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        print("🧹 VRAM Purged: Ready for FLUX.")

if __name__ == "__main__":
    purge()