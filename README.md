# TimeGenie-Reminder-Bot

TimeGenie is a handy Telegram bot designed to serve as your personal reminder assistant. Whether you want to remember to make a call, attend a meeting, or do anything else at a specific time, TimeGenie is here to make sure you never forget.

## Features

- **Personal Reminders**: Set reminders for yourself with a specific date and time. You will receive a reminder message at the appointed time.
- **Timezone Support**: With TimeGenie, you can set reminders in your local timezone. The bot supports a variety of timezone inputs to cater to users across the globe.
- **Simple Commands**: User-friendly command syntax makes it easy to set reminders.

## How It Works

TimeGenie operates by receiving and interpreting commands from users via Telegram. Once it receives a command to set a reminder, it parses the command, schedules the reminder, and stores it in an SQLite database. The reminders are then triggered at the specified time, and TimeGenie sends a reminder message to the user.

## Commands

- `/start`: Initializes the bot and provides instructions for setting a reminder.
- `/remind <date and time>, <reminder message>`: Sets a reminder. Acceptable date and time formats are "YYYY-MM-DD HH:MM AM/PM" or "YYYY-MM-DD HH:MM".

After setting a reminder, the bot will ask for your timezone to ensure that the reminder is set for the correct time.

## Prerequisites

- Python 3.6+
- python-telegram-bot
- pytz
- APScheduler
- SQLite

## Installation

1. Clone the repository to your local machine.
2. Install the required Python packages using pip: `pip install -r requirements.txt`.
3. Run the bot script: `python bot.py`.

Remember to replace the placeholder in the code with your actual bot token, which you can get from BotFather on Telegram.

## License

TimeGenie is open-sourced software licensed under the MIT license. 

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Disclaimer

Please be aware that the reminders are stored locally in an SQLite database and are not encrypted. Do not use TimeGenie to set reminders that include sensitive information.
