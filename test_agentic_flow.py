import os
import io
import asyncio
import logging
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Import your agentic modules
from orchestrator import orchestrator 
from vram_manager import purge as purge_vram 
from dotenv import load_dotenv

# --- CONFIGURATION ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_ID = int(os.getenv("MY_CHAT_ID"))
BASE_PATH = "/nuvodata/User_data/shiva/Market_carousal"
CSV_PATH = os.path.join(BASE_PATH, "marketing_plan.csv")
HISTORY_PATH = os.path.join(BASE_PATH, "topic_history.log")
OUTPUT_DIR = os.path.join(BASE_PATH, "output_slides")

# Logging setup

# --- 1. START HANDLER ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initial Command Center Menu"""
    if update.effective_user.id != MY_ID: 
        return
    
    keyboard = [
        [InlineKeyboardButton("🔍 Scout Market & Plan (Pro)", callback_data='cmd_plan')],
        [InlineKeyboardButton("🚀 Run Full Factory Batch", callback_data='cmd_generate')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💎 **Nueralogic Command Center (v2.0 Agentic)**\n"
        "Status: System Online\n"
        "VRAM Manager: Active\n\n"
        "Ready to build strategic content.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# --- 2. PHASE 2: PLANNING (ORCHESTRATOR) ---

async def handle_planning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers the LangGraph Orchestrator for Market Intel & Strategy"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🕵️‍♂️ **Agentic Flow Initiated...**\n"
        "1. Scouting Market Trends\n"
        "2. Querying Knowledge Base (RAG)\n"
        "3. Applying Marketing Frameworks (PAS/AIDA)\n"
        "4. Cleaning 'Rubbish' Fluff..."
    )
    
    try:
        # Load Topic History to avoid repetition
        past_topics = []
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, 'r') as f:
                past_topics = f.read().splitlines()[-15:]

        # Initial State for LangGraph
        initial_state = {
            "past_topics": past_topics,
            "scout_report": "",
            "kb_context": "",
            "proposed_calendar": "",
            "user_approval": False,
            "errors": []
        }
        
        # Invoke the Orchestrator
        # This runs Phase 1 (Scout) and Phase 2 (Strategist/Critic)
        result = orchestrator.invoke(initial_state)
        
        # Clean and Save the CSV output
        csv_raw = result["proposed_calendar"]
        csv_clean = csv_raw.strip().replace('```csv', '').replace('```', '').strip()
        
        with open(CSV_PATH, 'w') as f:
            f.write(csv_clean)

        # Generate a Human-Readable Preview
        df = pd.read_csv(io.StringIO(csv_clean), quotechar='"', skipinitialspace=True)
        summary = "📋 **Framework-Optimized Strategy:**\n\n"
        
        # Assuming Columns: Day, Framework, Topic, Angle...
        for _, row in df.head(5).iterrows():
            day = row.iloc[0]
            framework = row.iloc[1]
            angle = row.iloc[3]
            summary += f"🔹 **Day {day} ({framework})**: {angle}\n"

        keyboard = [
            [InlineKeyboardButton("✅ Approve & Batch Generate", callback_data='cmd_generate')],
            [InlineKeyboardButton("✍️ Refine/Re-Plan", callback_data='cmd_plan')]
        ]
        
        await query.message.reply_text(
            summary, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Planning Error: {traceback.format_exc()}")
        await query.message.reply_text(f"❌ **Strategy Error:**\n{str(e)}")

# --- 3. PHASE 3 & 4: PRODUCTION (FACTORY) ---

async def handle_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers the Batch Production Pipeline for all 5 days"""
    query = update.callback_query
    await query.answer()
    
    if not os.path.exists(CSV_PATH):
        await query.edit_message_text("❌ No plan found. Run 'Scout & Plan' first.")
        return

    # 1. Clear VRAM before starting heavy Flux tasks
    purge_vram()
    
    try:
        df = pd.read_csv(CSV_PATH, quotechar='"', skipinitialspace=True)
        day_col = df.columns[0]
        days = df[day_col].unique()
        
        await query.edit_message_text(
            f"⚙️ **Factory Online.**\nVRAM Purged. Processing {len(days)} days..."
        )

        for day in days:
            day_str = str(day).strip()
            clean_folder = day_str.replace(" ", "_")
            
            # Sub-step VRAM Purge to prevent OOM between days
            purge_vram()
            
            # Execute run_pipeline.py for the specific day
            process = await asyncio.create_subprocess_exec(
                'python', os.path.join(BASE_PATH, 'run_pipeline.py'), '--day', day_str,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Pipeline failed for {day_str}: {stderr.decode()}")
                await context.bot.send_message(chat_id=MY_ID, text=f"⚠️ Day {day_str} failed. Moving to next.")
                continue

            # Deliver PDF and Captions
            day_dir = os.path.join(OUTPUT_DIR, clean_folder)
            pdf_path = os.path.join(day_dir, "Nueralogic_Carousel.pdf")
            caption_path = os.path.join(day_dir, "social_captions.txt")
            
            caption_text = f"🚀 **Content Ready: Day {day_str}**"
            if os.path.exists(caption_path):
                with open(caption_path, 'r') as f:
                    caption_text += "\n\n" + f.read()[:900] # Telegram caption limit safety

            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=MY_ID, 
                        document=f, 
                        caption=caption_text,
                        parse_mode='Markdown'
                    )
        
        await query.message.reply_text("💎 **All professional assets delivered.**")

    except Exception as e:
        logger.error(f"Generation Error: {str(e)}")
        await query.message.reply_text(f"❌ **Factory Error:** {str(e)}")

# --- MAIN ---

def main():
    """Start the Bot"""
    logger.info("Starting bot initialization...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_planning, pattern='^cmd_plan$'))
    app.add_handler(CallbackQueryHandler(handle_generation, pattern='^cmd_generate$'))
    logger.info("Bot is ready. Starting polling... Send /start in Telegram.")
    app.run_polling()

if __name__ == "__main__":
    main()