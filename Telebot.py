import os
import logging
import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from dotenv import load_dotenv

# Import the compiled graph from your agent_react.py
from agent_react import app as langgraph_app

# ==============================
# 1. CONFIG & SECURITY
# ==============================
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

try:
    MY_ID = int(os.getenv("MY_CHAT_ID"))
except (TypeError, ValueError):
    MY_ID = None

# Logging setup for server monitoring
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ==============================
# 2. BOT LOGIC CLASS
# ==============================
class NueralogicBot:
    def __init__(self, token, agent):
        self.agent = agent
        self.app = (
            ApplicationBuilder()
            .token(token)
            .read_timeout(120)  # Increased for long Flux generation
            .write_timeout(120) # Increased for high-res PDF uploads
            .connect_timeout(60)
            .build()
        )

        # Register Commands
        self.app.add_handler(CommandHandler("reset", self.reset_conversation))
        # Register Message Handler
        self.app.add_handler(
            MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message)
        )

    # --- RESET CONVERSATION ---
    async def reset_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != MY_ID:
            return
        chat_id = str(update.effective_chat.id)
        config = {"configurable": {"thread_id": chat_id}}
        
        # Clears the LangGraph history for this thread
        self.agent.update_state(config, {"messages": []})
        await update.message.reply_text("🔄 **Memory Cleared**. Ready for a new campaign.")

    # --- HANDLE CHAT & AGENT ---
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Security Gate
        if update.effective_chat.id != MY_ID:
            await update.message.reply_text("🚫 Unauthorized Access.")
            return

        chat_id = str(update.effective_chat.id)
        user_text = update.message.text
        config = {"configurable": {"thread_id": chat_id}}

        # Show 'typing' while AI processes
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        try:
            async for event in self.agent.astream(
                {"messages": [HumanMessage(content=user_text)]},
                config,
                stream_mode="values",
            ):
                if not event.get("messages"):
                    continue
                last_msg = event["messages"][-1]

                # A. Tool Call Notification
                if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                    for tool_call in last_msg.tool_calls:
                        if tool_call["name"] == "generate_and_render_carousel":
                            await update.message.reply_text("🚀 **GPU Pipeline Active**: Generating Flux images on CUDA:4. Please wait ~1-2 minutes...")
                            await context.bot.send_chat_action(chat_id=chat_id, action="upload_document")

                # B. Text Response (with HTML bolding)
                elif isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
                    if last_msg.content.strip():
                        await update.message.reply_text(last_msg.content, parse_mode="HTML")

                # C. Tool Result Handling (Direct Path Extraction)
                elif isinstance(last_msg, ToolMessage):
                    content_str = str(last_msg.content)
                    if content_str.startswith("SUCCESS|"):
                        try:
                            # Split the return string: SUCCESS|pdf_path|image_dir
                            _, pdf_path, image_dir = content_str.split("|")
                            await self.send_campaign_files_direct(update, context, pdf_path, image_dir)
                        except ValueError:
                            logging.error(f"Malformed tool result: {content_str}")

        except Exception as e:
            logging.error(f"Agent Error: {e}")
            await update.message.reply_text(f"❌ **System Error**: {e}")

    # --- FILE DELIVERY ENGINE ---
    async def send_campaign_files_direct(self, update, context, pdf_path, image_dir):
        chat_id = update.effective_chat.id

        # 1. Send PNG Gallery
        if os.path.exists(image_dir):
            png_files = sorted([f for f in os.listdir(image_dir) if f.endswith(".png")])
            if png_files:
                media_group = []
                handles = []
                try:
                    for png in png_files[:10]: # Telegram limit is 10 per group
                        file_path = os.path.join(image_dir, png)
                        f = open(file_path, "rb")
                        handles.append(f)
                        media_group.append(InputMediaPhoto(media=f))
                    
                    await context.bot.send_media_group(chat_id=chat_id, media=media_group, write_timeout=120)
                except Exception as e:
                    logging.error(f"Gallery upload failed: {e}")
                finally:
                    # Crucial: Close all file handles after sending
                    for h in handles: h.close()

        # 2. Send PDF Document
        if os.path.exists(pdf_path):
            try:
                with open(pdf_path, "rb") as f:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        filename=os.path.basename(pdf_path),
                        caption="💎 **Nueralogic Strategy Ready**",
                        write_timeout=120
                    )
            except Exception as e:
                logging.error(f"PDF upload failed: {e}")
        else:
            await update.message.reply_text(f"⚠️ PDF not found on server: {pdf_path}")

    # --- RUN ---
    def run(self):
        print("🚀 Nueralogic Bot is active. Restricted to authorized ID.")
        self.app.run_polling()

# ==============================
# 3. EXECUTION
# ==============================
if __name__ == "__main__":
    if not TOKEN or not MY_ID:
        print("❌ CONFIG ERROR: Check your .env for TELEGRAM_TOKEN and MY_CHAT_ID.")
    else:
        bot = NueralogicBot(TOKEN, langgraph_app)
        bot.run()