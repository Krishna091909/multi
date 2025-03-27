import os
import json
import logging
import asyncio
import threading
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import PeerIdInvalid, FloodWait
from flask import Flask

# Enable logging for debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load config
API_ID = int(os.getenv("API_ID", "26742257"))
API_HASH = os.getenv("API_HASH", "625a7410153e4222aa34b82b9cff2554")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7609777584:AAEfshwUjKNEiT7RXag5Yu_tnzCAjIgkMug")

# Create bot instance
app = Client("MultiForwardBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load or create forwarding rules
FORWARD_FILE = "forward_rules.json"
if not os.path.exists(FORWARD_FILE):
    with open(FORWARD_FILE, "w") as f:
        json.dump({}, f)

def load_forward_rules():
    try:
        with open(FORWARD_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}  # Return empty dictionary if JSON is corrupted

def save_forward_rules(rules):
    with open(FORWARD_FILE, "w") as f:
        json.dump(rules, f, indent=4)

FORWARD_MAP = load_forward_rules()

# Command to add a forwarding rule
@app.on_message(filters.command("add_forward") & filters.private)
async def add_forward(client, message: Message):
    args = message.text.split()
    if len(args) != 3:
        await message.reply_text("Usage: /add_forward source_chat_id destination_chat_id")
        return

    source, dest = args[1], args[2]

    if source not in FORWARD_MAP:
        FORWARD_MAP[source] = []
    
    if dest not in FORWARD_MAP[source]:
        FORWARD_MAP[source].append(dest)
        save_forward_rules(FORWARD_MAP)
        await message.reply_text(f"✅ Added forwarding: {source} ➡ {dest}")
    else:
        await message.reply_text("⚠️ This forwarding rule already exists.")

# Command to remove a forwarding rule
@app.on_message(filters.command("remove_forward") & filters.private)
async def remove_forward(client, message: Message):
    args = message.text.split()
    if len(args) != 3:
        await message.reply_text("Usage: /remove_forward source_chat_id destination_chat_id")
        return

    source, dest = args[1], args[2]

    if source in FORWARD_MAP and dest in FORWARD_MAP[source]:
        FORWARD_MAP[source].remove(dest)
        if not FORWARD_MAP[source]:  
            del FORWARD_MAP[source]
        save_forward_rules(FORWARD_MAP)
        await message.reply_text(f"✅ Removed forwarding: {source} ❌ {dest}")
    else:
        await message.reply_text("⚠️ Forwarding rule not found.")

# Command to list all forwarding rules
@app.on_message(filters.command("list_forwards") & filters.private)
async def list_forwards(client, message: Message):
    if not FORWARD_MAP:
        await message.reply_text("ℹ️ No forwarding rules set.")
        return
    
    rules_text = "📜 **Current Forwarding Rules:**\n"
    for source, destinations in FORWARD_MAP.items():
        rules_text += f"🔹 `{source}` ➡ {', '.join(destinations)}\n"
    
    await message.reply_text(rules_text)

# Forward messages based on rules
@app.on_message()
async def forward_messages(client, message: Message):
    global FORWARD_MAP
    FORWARD_MAP = load_forward_rules()  # Reload rules dynamically

    source_id = str(message.chat.id)
    if source_id in FORWARD_MAP:
        for dest_id in FORWARD_MAP[source_id]:
            try:
                # Ensure the bot has access to the destination chat
                chat = await client.get_chat(int(dest_id))
                await message.forward(chat.id)
                logging.info(f"✅ Forwarded message from {source_id} to {dest_id}")
            except PeerIdInvalid:
                logging.error(f"❌ Invalid Peer ID: {dest_id}")
            except FloodWait as e:
                logging.warning(f"⏳ FloodWait triggered: Sleeping for {e.value} seconds")
                await asyncio.sleep(e.value)
            except Exception as e:
                logging.error(f"❌ Error forwarding to {dest_id}: {e}")

# Flask Web Server to Keep Alive
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running and forwarding messages!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# Start Flask in a separate thread
threading.Thread(target=run_flask, daemon=True).start()

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run()
