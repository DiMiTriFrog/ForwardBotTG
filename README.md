# Telegram Forwarder Bot

This bot forwards messages from a base group to multiple destination groups.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure the bot token:**
    - Rename `.env.example` to `.env`.
    - Open the `.env` file and replace `YOUR_BOT_TOKEN_HERE` with your actual Telegram Bot Token obtained from BotFather.
5.  **Run the bot:**
    ```bash
    python main.py
    ```

## Usage

1.  Start a chat with your bot on Telegram.
2.  Send `/start` to see the main menu.
3.  Add the bot to the groups you want to use (both base and destination groups).
4.  Use the bot's menu to configure the base group and destination groups:
    - You'll need to forward a message from the target group to the bot's private chat to register it.
5.  Once configured, the bot will automatically forward messages from the base group to the destination groups.

## Features

- Forward messages from one group to multiple others.
- Per-user configuration (each user can set up their own forwarding rules).
- SQLite database to store configurations.
- Prevents duplicate configurations (same base -> same destination).
- Intuitive menu with buttons for managing configurations.
