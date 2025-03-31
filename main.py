import logging
import signal
import sys
from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

import config
import database as db
import handlers

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    logger.info("Initializing database...")
    try:
        db.initialize_database()
    except Exception as e:
        logger.critical(f"FATAL: Could not initialize database: {e}")
        sys.exit(1) # Exit if DB initialization fails

    logger.info("Creating Telegram Application...")
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # --- Register Handlers ---
    # Command Handlers (private chat)
    application.add_handler(CommandHandler("start", handlers.start, filters=filters.ChatType.PRIVATE))

    # Callback Query Handler (button presses)
    application.add_handler(CallbackQueryHandler(handlers.button_callback_handler))

    # Message Handlers
    # 1. Handle forwarded messages in private chat for setup
    application.add_handler(MessageHandler(
        filters.FORWARDED & filters.ChatType.PRIVATE,
        handlers.handle_forwarded_message
    ))

    # 2. Handle regular messages in groups/channels for forwarding
    #    - Only in groups/supergroups/channels
    #    - Ignore commands (/...) in groups
    #    - Ignore edited messages (can cause issues with forwarding)
    application.add_handler(MessageHandler(
        (filters.ChatType.GROUPS | filters.ChatType.CHANNEL)
        & ~filters.COMMAND
        & ~filters.UpdateType.EDITED_MESSAGE
        & ~filters.UpdateType.EDITED_CHANNEL_POST,
        handlers.handle_group_message
    ))

    # Error Handler
    application.add_error_handler(handlers.error_handler)

    # Graceful shutdown handler
    def signal_handler(sig, frame):
        logger.info("Received signal to stop. Shutting down gracefully...")
        # Close DB connection pool or thread-local connections if necessary
        try:
            db.close_db_connection() # Close connection for the main thread
            logger.info("Database connections closed (main thread). Exiting.")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
        # PTB Application shutdown is handled by run_polling on SIGINT/TERM/ABRT

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot polling...")
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True, # Ignore messages received while bot was offline
            close_loop=False           # Allows for cleaner shutdown
        )
    except Exception as e:
        logger.critical(f"Error during polling: {e}")
    finally:
        # Close DB connection on clean exit 
        logger.info("Closing main thread DB connection post-polling.")
        try:
            db.close_db_connection()
        except Exception as e:
            logger.error(f"Error closing database connections on shutdown: {e}")

if __name__ == "__main__":
    main() 