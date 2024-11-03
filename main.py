import logging
import os
import sqlite3
from datetime import datetime
import pytz
from dateparser import parse as parse_date
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler,
    MessageHandler, filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load the Telegram Bot API token from an environment variable
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    logging.error("The TELEGRAM_BOT_TOKEN environment variable is not set.")
    exit(1)

# Initialize the database
def init_db():
    with sqlite3.connect('reminders.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                reminder_time TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)
        conn.commit()

# Function to insert a reminder into the database
def insert_reminder(chat_id, reminder_time, message):
    with sqlite3.connect('reminders.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (chat_id, reminder_time, message) VALUES (?, ?, ?)",
            (chat_id, reminder_time, message)
        )
        conn.commit()
        return cursor.lastrowid

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to TimeGenie! Use /remind to set a reminder."
    )

# Conversation states
ASK_TIME, ASK_MESSAGE = range(2)

# /remind command handler
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "When should I remind you? (e.g., 'in 2 hours', 'tomorrow at 9am')"
    )
    return ASK_TIME

# Handle time input
async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    reminder_time = parse_date(user_input, settings={'RETURN_AS_TIMEZONE_AWARE': True})
    if reminder_time is None:
        await update.message.reply_text("I couldn't understand that time. Please try again.")
        return ASK_TIME

    # Convert to UTC
    reminder_time = reminder_time.astimezone(pytz.utc)
    now = datetime.now(pytz.utc)
    if reminder_time < now:
        await update.message.reply_text("That time is in the past! Please enter a future time.")
        return ASK_TIME

    context.user_data['reminder_time'] = reminder_time
    await update.message.reply_text("What should I remind you about?")
    return ASK_MESSAGE

# Handle message input
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    reminder_time = context.user_data['reminder_time']
    chat_id = update.message.chat_id

    # Insert reminder into the database
    reminder_id = insert_reminder(chat_id, reminder_time.isoformat(), message)

    # Schedule the reminder
    context.job_queue.run_once(
        send_reminder,
        when=reminder_time,
        chat_id=chat_id,
        data={'message': message},
        name=str(reminder_id)
    )

    await update.message.reply_text(
        f"Reminder set for {reminder_time.strftime('%Y-%m-%d %H:%M:%S %Z')}!"
    )
    return ConversationHandler.END

# Function to send a reminder
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    message = context.job.data['message']
    await context.bot.send_message(chat_id=context.job.chat_id, text=f"⏰ Reminder: {message}")

# Cancel command handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Reminder creation cancelled.")
    return ConversationHandler.END

# /list command handler
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    with sqlite3.connect('reminders.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, reminder_time, message FROM reminders WHERE chat_id = ? ORDER BY reminder_time",
            (chat_id,)
        )
        rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("You have no upcoming reminders.")
        return

    messages = []
    for row in rows:
        reminder_id, reminder_time_str, message = row
        reminder_time = datetime.fromisoformat(reminder_time_str)
        reminder_time = reminder_time.astimezone(pytz.utc)
        time_str = reminder_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        messages.append(
            f"ID: {reminder_id}\nTime: {time_str}\nMessage: {message}\n"
        )

    await update.message.reply_text("\n".join(messages))

# /delete command handler
async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete <reminder_id>")
        return

    reminder_id = context.args[0]
    if not reminder_id.isdigit():
        await update.message.reply_text("Reminder ID must be a number.")
        return

    reminder_id = int(reminder_id)
    chat_id = update.message.chat_id

    with sqlite3.connect('reminders.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM reminders WHERE id = ? AND chat_id = ?",
            (reminder_id, chat_id)
        )
        conn.commit()

    # Remove job from job queue
    jobs = context.job_queue.get_jobs_by_name(str(reminder_id))
    if jobs:
        for job in jobs:
            job.schedule_removal()
        await update.message.reply_text("Reminder deleted successfully.")
    else:
        await update.message.reply_text("No such reminder found.")

# Main function to run the bot
def main():
    init_db()
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('remind', remind)],
        states={
            ASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time)],
            ASK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('list', list_reminders))
    application.add_handler(CommandHandler('delete', delete_reminder))

    application.run_polling()

if __name__ == '__main__':
    main()
