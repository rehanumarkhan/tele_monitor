import re
import asyncio
import requests
import pytz
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import os
import signal
import tempfile
import json
from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd

# Your API ID and Hash from my.telegram.org
api_id = 'replace with api_id'
api_hash = 'replace with api_hash'
phone = 'replace with phone number'

# Bot token and chat ID for notifications
bot_token = 'replace with bot token'
notification_chat_id = -replace # Your chat ID or the ID of the group/channel you want to send notifications to
formatted_notification_chat_id = f"-100{abs(notification_chat_id)}"

# Keywords to monitor
keywords = set(['keyword1', 'keyword2'])

# Set to track processed message IDs to prevent duplicates
processed_message_ids = set()

# Time zone setup for Abu Dhabi
abu_dhabi_tz = pytz.timezone('Asia/Dubai')

# Create the Telegram client
client = TelegramClient('session_name', api_id, api_hash)

# Initialize logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', filename='telegram_bot.log', filemode='w')
logger = logging.getLogger()

# Store matched messages for the daily report
matched_messages = []

# Store messages with additional metadata for advanced reporting
detailed_messages = []

# Create a queue to manage incoming messages
message_queue = asyncio.Queue()
max_concurrent_downloads = 3  # Limit the number of concurrent downloads

# Track recent notifications to avoid duplicates
recent_notifications = []

# Initialize a dictionary to track keyword occurrences
keyword_trends = defaultdict(list)


async def send_notification(message, image_path=None):
    """Send notification with optional image."""
    try:
        payload = {
            'chat_id': formatted_notification_chat_id,
            'text': message,
            'parse_mode': 'Markdown'  # Enables Markdown formatting
        }
        response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', data=payload)
        response.raise_for_status()

        if image_path:
            with open(image_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {'chat_id': formatted_notification_chat_id, 'caption': 'Image with matched keyword'}
                response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendPhoto', files=files, data=data)
                response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending notification: {e}")


def clean_message_text(message_text):
    """Clean unwanted characters and multiple blank lines from message."""
    return re.sub(r'\s+', ' ', re.sub(r'\|.*?\|', '', message_text)).strip()


async def track_keyword_trends(keyword, date):
    """Record the date and keyword occurrence."""
    keyword_trends[keyword].append(date)


async def generate_trend_report(event):
    """Generate and send keyword trend report."""
    data = [{'keyword': k, 'date': d} for k, dates in keyword_trends.items() for d in dates]
    df = pd.DataFrame(data)

    # Ensure date column is of datetime type
    df['date'] = pd.to_datetime(df['date'])

    # Filter data for the last 30 days
    recent_days = datetime.now() - timedelta(days=30)
    df = df[df['date'] >= recent_days]

    # Check if the DataFrame is empty after filtering
    if df.empty:
        await send_notification("⚠️ *No data available for the trend report in the last 30 days.*")
        return

    # Count occurrences per day
    trend_data = df.groupby([df['date'].dt.date, 'keyword']).size().unstack(fill_value=0)

    # Plot the trend data
    plt.figure(figsize=(10, 6))
    trend_data.plot(kind='line', ax=plt.gca())
    plt.title('Keyword Trend Analysis')
    plt.xlabel('Date')
    plt.ylabel('Frequency')
    plt.grid(True)
    plt.legend(title='Keywords')

    # Save the plot as an image
    plot_path = 'trend_report.png'
    plt.savefig(plot_path)

    # Send the trend report image
    await send_notification("📊 *Keyword Trend Report:*", image_path=plot_path)

    # Clear the plot
    plt.close()


async def process_plain_text_message(event):
    """Process plain text messages."""
    message_text = event.message.message.lower()
    await process_message(event, message_text, image_path=None)


async def process_message(event, message_text, image_path=None):
    """Process and notify on matching messages."""
    chat = await event.get_chat()
    sender = await event.get_sender()

    # Skip messages from the notification chat or the bot itself
    if chat.id == notification_chat_id or (hasattr(sender, 'bot') and sender.bot):
        logger.info("Message from notification group or bot skipped.")
        return

    sender_name = sender.username if sender and sender.username else sender.first_name or 'Unknown'
    chat_name = chat.title if hasattr(chat, 'title') else 'Private Chat'
    message_link = f'https://t.me/{chat.username}/{event.message.id}' if hasattr(chat, 'username') else 'N/A'

    # Convert to Abu Dhabi time zone
    abu_dhabi_dt = event.message.date.astimezone(abu_dhabi_tz)
    date = abu_dhabi_dt.strftime('%Y-%m-%d %H:%M:%S')

    # Clean the message text
    message_text = clean_message_text(message_text)

    keyword_matched = False
    for keyword in keywords:
        if keyword in message_text:
            keyword_matched = True
            notification_message = (
                f"🔍 *Keyword Matched:* `{keyword}` (from {'image' if image_path else 'text'})\n"
                f"👤 *Sender:* `{sender_name}`\n"
                f"🏷️ *Chat Title:* `{chat_name}`\n"
                f"📅 *Date:* `{date}`\n"
                f"🔗 *Message Link:* [link]({message_link})"
            )
            if not image_path:
                notification_message += f"\n✉️ *Message:* `{message_text}`"

            logger.info(notification_message)

            # Avoid sending duplicate notifications
            if notification_message not in recent_notifications:
                await send_notification(notification_message, image_path)
                recent_notifications.append(notification_message)
                if len(recent_notifications) > 50:
                    recent_notifications.pop(0)

            # Save the matched message for daily summary and detailed report
            matched_messages.append(notification_message)
            detailed_messages.append({
                'keyword': keyword,
                'message': message_text if not image_path else 'Image matched',
                'sender_name': sender_name,
                'chat_name': chat_name,
                'date': date,
                'message_link': message_link
            })
            break

    # Track keyword trends if matched
    if keyword_matched:
        await track_keyword_trends(keyword, date)


async def download_and_process_image(event):
    """Download and process images for keyword matches."""
    logger.info("Starting file download...")
    try:
        file = await event.message.download_media(file=BytesIO())
        logger.info("File download complete. Processing image...")

        image = Image.open(file)
        message_text = pytesseract.image_to_string(image).lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            image_path = tmp.name
            image.save(image_path)

        await process_message(event, message_text, image_path=image_path)
        logger.info("Image processing complete.")

        os.remove(image_path)
    except UnidentifiedImageError:
        logger.error("Downloaded file is not a valid image. Skipping processing.")
    except Exception as e:
        logger.error(f"Error during image processing: {e}")


@client.on(events.NewMessage)
async def handler(event):
    """Handle incoming messages."""
    try:
        await message_queue.put(event)
    except Exception as e:
        logger.error(f"Error handling new message: {e}")


async def message_worker():
    """Worker to process queued messages."""
    while True:
        event = await message_queue.get()
        try:
            if event.message.id not in processed_message_ids:
                processed_message_ids.add(event.message.id)
                if event.message.message:
                    await process_plain_text_message(event)
                if event.message.media:
                    if hasattr(event.message.media, 'document'):
                        await download_and_process_image(event)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
        finally:
            message_queue.task_done()


@client.on(events.NewMessage(pattern='/addkeyword (.*)'))
async def add_keyword(event):
    """Add a keyword to monitor."""
    try:
        new_keyword = event.pattern_match.group(1).strip()
        if new_keyword and new_keyword not in keywords:
            keywords.add(new_keyword)
            await event.reply(f"➕ *Keyword* `{new_keyword}` *added.*")
        else:
            await event.reply(f"⚠️ *Keyword* `{new_keyword}` *already exists or is invalid.*")
    except Exception as e:
        logger.error(f"Error adding keyword: {e}")


@client.on(events.NewMessage(pattern='/removekeyword (.*)'))
async def remove_keyword(event):
    """Remove a monitored keyword."""
    try:
        keyword_to_remove = event.pattern_match.group(1).strip()
        if keyword_to_remove in keywords:
            keywords.remove(keyword_to_remove)
            await event.reply(f"❌ *Keyword* `{keyword_to_remove}` *removed.*")
        else:
            await event.reply(f"⚠️ *Keyword* `{keyword_to_remove}` *not found.*")
    except Exception as e:
        logger.error(f"Error removing keyword: {e}")


@client.on(events.NewMessage(pattern='/listkeywords'))
async def list_keywords(event):
    """List all monitored keywords."""
    try:
        message = "🔍 *Current Keywords:*\n" + ", ".join([f"`{kw}`" for kw in keywords])
        await event.reply(message)
    except Exception as e:
        logger.error(f"Error listing keywords: {e}")


@client.on(events.NewMessage(pattern='/startbot'))
async def start_bot(event):
    """Start the bot."""
    try:
        await event.reply("🟢 *Bot is already running.*")
    except Exception as e:
        logger.error(f"Error in start bot command: {e}")


@client.on(events.NewMessage(pattern='/stopbot'))
async def stop_bot(event):
    """Stop the bot."""
    try:
        await event.reply("🛑 *Stopping bot...*")
        await client.disconnect()
    except Exception as e:
        logger.error(f"Error in stop bot command: {e}")


@client.on(events.NewMessage(pattern='/restartbot'))
async def restart_bot(event):
    """Restart the bot."""
    try:
        await event.reply("🔄 *Restarting bot...*")
        os.kill(os.getpid(), signal.SIGTERM)  # Gracefully terminate the current process
    except Exception as e:
        logger.error(f"Error in restart bot command: {e}")


@client.on(events.NewMessage(pattern='/report'))
async def generate_report(event):
    """Generate a report."""
    try:
        report_type = event.message.message.split()[1] if len(event.message.message.split()) > 1 else 'daily'
        if report_type == 'daily':
            await send_daily_summary(report_now=True)
        else:
            await event.reply("⚠️ *Unsupported report type. Available options: /report daily*")
    except Exception as e:
        logger.error(f"Error generating report: {e}")


@client.on(events.NewMessage(pattern='/reportbykeyword (.*)'))
async def report_by_keyword(event):
    """Generate a report filtered by keyword."""
    try:
        keyword = event.pattern_match.group(1).strip().lower()
        report = [msg for msg in detailed_messages if msg['keyword'] == keyword]
        if report:
            report_message = f"🔍 *Report for keyword* `{keyword}`:\n\n" + "\n\n".join(
                [json.dumps(msg, indent=4) for msg in report])
            await send_notification(report_message)
        else:
            await event.reply(f"⚠️ *No messages found for keyword* `{keyword}`.")
    except Exception as e:
        logger.error(f"Error in report by keyword command: {e}")


@client.on(events.NewMessage(pattern='/reportbydate (.*)'))
async def report_by_date(event):
    """Generate a report filtered by date."""
    try:
        date_str = event.pattern_match.group(1).strip()
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        report = [msg for msg in detailed_messages if
                  datetime.strptime(msg['date'], '%Y-%m-%d %H:%M:%S').date() == target_date]
        if report:
            report_message = f"📅 *Report for date* `{date_str}`:\n\n" + "\n\n".join(
                [json.dumps(msg, indent=4) for msg in report])
            await send_notification(report_message)
        else:
            await event.reply(f"⚠️ *No messages found for date* `{date_str}`.")
    except ValueError:
        await event.reply(f"⚠️ *Invalid date format* `{date_str}`. *Please use YYYY-MM-DD format.*")
    except Exception as e:
        logger.error(f"Error in report by date command: {e}")


@client.on(events.NewMessage(pattern='/reportbychat (.*)'))
async def report_by_chat(event):
    """Generate a report filtered by chat name."""
    try:
        chat_name = event.pattern_match.group(1).strip().lower()
        report = [msg for msg in detailed_messages if msg['chat_name'].lower() == chat_name]
        if report:
            report_message = f"🏷️ *Report for chat* `{chat_name}`:\n\n" + "\n\n".join(
                [json.dumps(msg, indent=4) for msg in report])
            await send_notification(report_message)
        else:
            await event.reply(f"⚠️ *No messages found for chat* `{chat_name}`.")
    except Exception as e:
        logger.error(f"Error in report by chat command: {e}")


async def send_daily_summary(report_now=False):
    """Send a daily summary report."""
    now = datetime.now(abu_dhabi_tz)
    target_time = now.replace(hour=23, minute=59, second=0, microsecond=0)
    if now > target_time or report_now:
        if matched_messages:
            summary_message = "🗓️ *Daily Summary Report:*\n\n" + "\n\n".join(matched_messages)
            await send_notification(summary_message)
            matched_messages.clear()
    if not report_now:
        await asyncio.sleep((target_time - now).total_seconds())


async def keep_alive():
    """Send a keep-alive ping to maintain the connection."""
    while True:
        try:
            await asyncio.sleep(3600)  # Sends a ping every hour to keep the connection alive
            logger.info("Sending keep-alive ping.")
            await client.send_message('me', 'keep-alive')
        except Exception as e:
            logger.error(f"Error in keep_alive: {e}")


async def main():
    """Main function to start the client."""
    try:
        await client.start(phone)
        client.loop.create_task(keep_alive())
        client.loop.create_task(send_daily_summary())

        # Start worker tasks to process messages
        for _ in range(max_concurrent_downloads):
            client.loop.create_task(message_worker())

        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Error in main function: {e}")


# Start the client and run it until disconnected
try:
    asyncio.run(main())
except Exception as e:
    logger.error(f"Error running main: {e}")
