import logging
import os
import sqlite3
from datetime import datetime
from pytz import timezone, UnknownTimeZoneError
from telegram import Update, ReplyKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Load the Telegram Bot API token from an environment variable
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    logging.error("The TELEGRAM_BOT_TOKEN environment variable is not set.")
    exit(1)

# Initialize the scheduler with UTC timezone
scheduler = BackgroundScheduler()
scheduler.start()

# Initialize the database
def init_db():
    with sqlite3.connect('reminders.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                chat_id INTEGER,
                reminder_time TEXT,
                message TEXT
            )
        """)
        conn.commit()

# Function to insert a reminder into the database
def insert_reminder(chat_id, reminder_time, message):
    with sqlite3.connect('reminders.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reminders (chat_id, reminder_time, message) VALUES (?, ?, ?)", (chat_id, reminder_time, message))
        conn.commit()

# Function to send a reminder
def send_reminder(context: CallbackContext):
    job_context = context.job.context
    context.bot.send_message(chat_id=job_context['chat_id'], text=f"Reminder: {job_context['message']}")

# Start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Welcome to TimeGenie! Use /remind <date and time>, <message> to set a reminder."
    )

# Function to handle the reminder command
def handle_reminder(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        reminder_cmd, date_str, message = update.message.text.split(',', 2)
        # Attempt to parse the date
        reminder_time = datetime.strptime(date_str.strip(), '%Y-%m-%d %H:%M')
        # Convert to UTC and schedule the reminder
        utc_reminder_time = reminder_time.astimezone(timezone('UTC'))
        insert_reminder(chat_id, utc_reminder_time.strftime('%Y-%m-%d %H:%M:%S'), message.strip())
        scheduler.add_job(send_reminder, 'date', run_date=utc_reminder_time, args=[{'chat_id': chat_id, 'message': message.strip()}])
        update.message.reply_text("Reminder set successfully!")
    except ValueError:
        update.message.reply_text("Incorrect date format. Please use YYYY-MM-DD HH:MM.")

# Function to initialize the bot
def main():
    init_db()
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('remind', handle_reminder))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
