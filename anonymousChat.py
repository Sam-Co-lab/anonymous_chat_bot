import os
import time
import re
import requests
import base64
import pickle
import random
import logging
from telegram import Update, Bot, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from telegram.error import BadRequest

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get('GitAccToken')
REPO_OWNER = "Sam-Co-lab"
REPO_NAME = "Data"
FILE_PATH = "userData.pkl"

GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# Load pickle file from GitHub
def load_data():
    try:
        response = requests.get(GITHUB_API_URL, headers=HEADERS)
        response.raise_for_status()
        content = response.json()["content"]
        return pickle.loads(base64.b64decode(content))
    except Exception:
        return {}

# Update pickle file on GitHub
def update_data(data):
    try:
        response = requests.get(GITHUB_API_URL, headers=HEADERS)
        sha = response.json().get("sha", "")
        encoded_data = base64.b64encode(pickle.dumps(data)).decode()

        payload = {
            "message": "Update user data",
            "content": encoded_data,
            "sha": sha,
        }
        requests.put(GITHUB_API_URL, headers=HEADERS, json=payload)
    except Exception as e:
        logger.error(f"Error updating data: {e}")

# Initialize user data
data = load_data()
active_chats = {}

# Start command handler
def start(update: Update, context: CallbackContext):
    logger.info("Received /start command")
    user_id = update.effective_user.id
    if user_id not in data:
        data[user_id] = {"name": None, "age": None, "gender": None}
        update_data(data)
        update.message.reply_text("Welcome! Please enter your name:")
        context.user_data["updating"] = "name"
    else:
        keyboard = [
            [InlineKeyboardButton("Start a Chat", callback_data="start_chat")],
            [InlineKeyboardButton("End Chat", callback_data="end_chat")],
            [InlineKeyboardButton("Settings", callback_data="settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "Welcome back! Please choose an option:", reply_markup=reply_markup
        )

# Handle button presses
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "start_chat":
        if user_id in active_chats:
            query.answer("You're already in a chat!")
        else:
            available_users = [uid for uid in data if uid not in active_chats and uid != user_id]
            if available_users:
                partner_id = random.choice(available_users)
                active_chats[user_id] = partner_id
                active_chats[partner_id] = user_id
                query.answer("Chat started!")

                context.bot.send_message(user_id, "You've been connected to a chat! Say hi!")
                context.bot.send_message(partner_id, "You've been connected to a chat! Say hi!")
            else:
                query.answer("No users available to chat right now.")

    elif query.data == "end_chat":
        if user_id in active_chats:
            partner_id = active_chats.pop(user_id)
            active_chats.pop(partner_id, None)

            context.bot.send_message(user_id, "You have left the chat.")
            context.bot.send_message(partner_id, "The other user has left the chat.")
        else:
            query.answer("You're not in a chat.")

    elif query.data == "settings":
        query.answer()
        context.bot.send_message(user_id, "Please enter your name:")
        context.user_data["updating"] = "name"

# Handle user messages
def message_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if "updating" in context.user_data:
        field = context.user_data.pop("updating")
        data[user_id][field] = update.message.text

        if field == "name":
            update.message.reply_text("Please enter your age:")
            context.user_data["updating"] = "age"
        elif field == "age":
            update.message.reply_text("Please enter your gender:")
            context.user_data["updating"] = "gender"
        elif field == "gender":
            update.message.reply_text("Your profile has been updated!")
            update_data(data)

    elif user_id in active_chats:
        partner_id = active_chats[user_id]
        context.bot.send_message(partner_id, update.message.text)

# Main function
def main():
    # Replace with your actual Telegram Bot API token
    bot_token = '7256270773:AAGccvp6zUWHQaLzcaJKM6oYCGNnqebuHU0'
    updater = Updater(bot_token)

    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

    # Start the webhook to listen for messages
    updater.start_webhook(listen='0.0.0.0',
                          port=int(os.environ.get('PORT', 5000)),
                          url_path=bot_token,
                          webhook_url=f'https://telegrambot-msio.onrender.com/{bot_token}')

    updater.idle()

if __name__ == "__main__":
    main()
