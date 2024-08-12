# Telegram Monitoring Bot

## Overview

This Telegram bot is designed to monitor messages in specified Telegram groups or channels for predefined keywords. It provides real-time notifications, daily summaries, and detailed reports. The bot can process both text and images, making it a versatile tool for monitoring a wide range of conversations.

## Features

- **Real-time Notifications:** Receive instant notifications when a keyword is matched in a monitored chat.
- **Daily Summaries:** Get a daily summary report of all matched messages.
- **Keyword Management:** Add or remove keywords directly through Telegram commands.
- **Support for Image Processing:** The bot can process images for keyword matches using OCR.
- **Customizable:** Easily modify the bot to suit your specific monitoring needs.

## Installation

### Prerequisites

- Python 3.7+
- A Telegram account
- [Telethon](https://docs.telethon.dev/en/stable/) - A Python library for interacting with the Telegram API.
- [PIL (Pillow)](https://pillow.readthedocs.io/en/stable/) - A Python Imaging Library.
- [pytesseract](https://pypi.org/project/pytesseract/) - A Python wrapper for Google's Tesseract-OCR Engine.
- [Matplotlib](https://matplotlib.org/) - A plotting library for generating reports.

### Setup

1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/telegram-monitoring-bot.git
    cd telegram-monitoring-bot
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Set up your Telegram API credentials:
   - Obtain your `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org).
   - Replace the placeholders in the script with your `api_id`, `api_hash`, and your Telegram phone number.

4. Configure the bot token and chat ID:
   - Obtain a bot token from the [BotFather](https://core.telegram.org/bots#botfather).
   - Replace the placeholders in the script with your bot token and the chat ID where notifications should be sent.

5. Run the bot:
    ```bash
    python telegram_bot.py
    ```

## Usage

### Bot Commands

- `/addkeyword <keyword>` - Add a new keyword to monitor.
- `/removekeyword <keyword>` - Remove a monitored keyword.
- `/listkeywords` - List all currently monitored keywords.
- `/trendreport` - Generate a trend report for monitored keywords.
- `/report` - Generate a daily summary report.
- `/reportbykeyword <keyword>` - Generate a report filtered by a specific keyword.
- `/reportbydate <YYYY-MM-DD>` - Generate a report filtered by a specific date.
- `/reportbychat <chat name>` - Generate a report filtered by chat name.
- `/startbot` - Start the bot.
- `/stopbot` - Stop the bot.
- `/restartbot` - Restart the bot.

### Customization

- **Keywords:** The set of keywords to monitor can be customized directly within the script or through the bot commands.
- **Notifications:** Customize the format and content of the notifications sent to your Telegram chat.
