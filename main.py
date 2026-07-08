import json
import asyncio
import threading
import os
import sys
import time
import sqlite3
from pyrogram import Client, idle
from flask import Flask
from BOT.plans.plan1 import check_and_expire_plans as plan1_expiry
import nest_asyncio

# Load bot credentials
with open("FILES/config.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)
    API_ID = DATA["36477371"]
    API_HASH = DATA["3a76d9743d5ea0c5c2a6c0e935e7bd56"]
    BOT_TOKEN = DATA["5408477690:AAHAbL3Q2B-wsRLBYjkqtZofU4rpVuLAiOA"]

# Pyrogram plugins - Load from BOT only
plugins = dict(root="BOT")

# Clean up any existing session files to prevent lock issues
def cleanup_session_files():
    """Remove any existing session files to prevent database lock issues"""
    session_files = ["MY_BOT.session", "MY_BOT.session-journal"]
    for session_file in session_files:
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                print(f"🗑️ Removed existing session file: {session_file}")
                time.sleep(1)  # Give OS time to release file locks
            except Exception as e:
                print(f"⚠️ Could not remove {session_file}: {e}")

# Run cleanup before creating client
cleanup_session_files()

# Pyrogram client with explicit session directory
bot = Client(
    "MY_BOT",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=plugins,
    workdir=".",  # Explicitly set work directory
    sleep_threshold=30  # Increase sleep threshold to avoid connection issues
)

# Flask App
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    """Run Flask server with error handling"""
    try:
        app.run(host="0.0.0.0", port=3000, debug=False, threaded=True)
    except Exception as e:
        print(f"❌ Flask server error: {e}")

async def run_bot():
    """Run the Telegram bot with proper error handling"""
    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"🚀 Starting bot (Attempt {attempt + 1}/{max_retries})...")
            await bot.start()
            print("✅ Bot started successfully!")

            # Start plan expiry checker
            asyncio.create_task(plan1_expiry(bot))

            # Keep the bot running
            await idle()

            break  # Success, exit retry loop

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print(f"⚠️ Database locked, retrying in {retry_delay} seconds...")
                if attempt < max_retries - 1:
                    await bot.stop()
                    time.sleep(retry_delay)
                    # Clean session files before retry
                    cleanup_session_files()
                    continue
                else:
                    print("❌ Max retries reached. Could not start bot.")
                    raise
            else:
                raise
        except Exception as e:
            print(f"❌ Bot startup error: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            else:
                raise
        finally:
            # Ensure bot is stopped properly
            try:
                await bot.stop()
                print("🛑 Bot stopped.")
            except:
                pass

if __name__ == "__main__":
    nest_asyncio.apply()

    print("=" * 50)
    print("🤖 BOT STARTUP SEQUENCE")
    print("=" * 50)

    # Start Flask in a daemon thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Flask server started on port 3000")

    # Give Flask a moment to start
    time.sleep(2)

    # Run the bot
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
