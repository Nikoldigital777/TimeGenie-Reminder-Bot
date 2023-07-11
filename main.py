import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters
from datetime import datetime
from pytz import timezone
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(timezone=timezone('UTC'))
scheduler.start()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
updater = Updater(token='placeholder', use_context=True)
dispatcher = updater.dispatcher


def send_reminder(context: CallbackContext):
    job_context = context.job.context
    chat_id = job_context['chat_id']
    message = job_context['message']
    context.bot.send_message(chat_id=chat_id, text=f"Reminder: {message}")


def start(update: Update, context: CallbackContext):
    accepted_formats = "- YYYY-MM-DD HH:MM AM/PM\n- YYYY-MM-DD HH:MM"
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Welcome to TimeGenie! I'm here to help you remember all important things. To set a reminder, use the following formats:\n\n/remind <date and time>, <reminder message>\n\nAccepted date and time formats:\n{accepted_formats}")
    return 'REMINDER_INPUT'


def handle_reminder_input(update: Update, context: CallbackContext):
    message = update.message.text
    chat_id = update.effective_chat.id

    try:
        _, reminder = message.split(' ', 1)
        date_string, reminder_message = reminder.split(',', 1)
        try:
            date = datetime.strptime(date_string.strip(), "%Y-%m-%d %I:%M %p")
        except ValueError:
            try:
                date = datetime.strptime(date_string.strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                context.bot.send_message(chat_id=chat_id,
                                         text="Sorry, I couldn't understand the reminder format. Please use the accepted formats:\n\n/remind <date and time>, <reminder message>")
                return ConversationHandler.END
        context.user_data['pending_reminder'] = {
            'date': date,
            'message': reminder_message.strip()
        }
        keyboard = [['US/Pacific', 'US/Mountain'], ['US/Central', 'US/Eastern']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        context.bot.send_message(chat_id=chat_id, text="Please select your timezone:", reply_markup=reply_markup)
        return 'TIMEZONE_SELECTION'
    except ValueError:
        context.bot.send_message(chat_id=chat_id,
                                 text="Sorry, I couldn't understand the reminder format. Please use the accepted formats:\n\n/remind <date and time>, <reminder message>")
        return ConversationHandler.END


def handle_timezone_selection(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    selected_timezone = update.message.text
    pending_reminder = context.user_data.get('pending_reminder')

    if pending_reminder is None:
        context.bot.send_message(chat_id=chat_id, text="There was an error processing your reminder.")
        return ConversationHandler.END

    date = pending_reminder['date']
    reminder_message = pending_reminder['message']

    try:
        timezone_obj = timezone(selected_timezone)
        localized_date = timezone_obj.localize(date)
        utc_date = localized_date.astimezone(timezone('UTC'))
    except timezone.UnknownTimeZoneError:
        context.bot.send_message(chat_id=chat_id, text="Sorry, the selected timezone is invalid.")
        return ConversationHandler.END

    with sqlite3.connect('reminders.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO reminders VALUES (?, ?, ?)",
                           (chat_id, utc_date.isoformat(), reminder_message.strip()))
            conn.commit()
            scheduler.add_job(send_reminder, 'date', run_date=utc_date,
                              args=[{'chat_id': chat_id, 'message': reminder_message.strip()}], timezone='UTC')
            confirmation_text = f"Okay, I will remind you on {localized_date.strftime('%Y-%m-%d %H:%M:%S')} in {selected_timezone}: {reminder_message}"
            context.bot.send_message(chat_id=chat_id, text=confirmation_text)
        except sqlite3.Error as e:
            logging.error(f"Error executing database query: {e}")

    del context.user_data['pending_reminder']

    return ConversationHandler.END


reminder_handler = ConversationHandler(
    entry_points=[CommandHandler('remind', handle_reminder_input)],
    states={
        'REMINDER_INPUT': [MessageHandler(Filters.text & ~Filters.command, handle_reminder_input)],
        'TIMEZONE_SELECTION': [MessageHandler(Filters.text & ~Filters.command, handle_timezone_selection)],
    },
    fallbacks=[],
)

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(reminder_handler)

updater.start_polling()
