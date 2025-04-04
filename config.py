import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "password123")  # Default password if not set

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables. Make sure to set it in the .env file.")

DATABASE_NAME = "forwarder_bot.sqlite3" 