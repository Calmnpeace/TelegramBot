from flask import Flask, request
import telebot
import os
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load Telegram Bot Token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
bot = telebot.TeleBot(TOKEN)

# Flask app for handling webhooks
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json()
        bot.process_new_updates([telebot.types.Update.de_json(json_data)])
        return "OK", 200
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return "Internal Server Error", 500

# Command Handlers
@bot.message_handler(commands=["start"])
def handle_start(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name

        # Send data to the ngrok-hosted API
        api_url = "https://f536-218-111-149-235.ngrok-free.app/products"  # Replace with your actual ngrok URL
        payload = {
            "category": 'Users',
            "name": first_name,
            "price": user_id,
            "quantity": "2"
        }
        response = requests.post(api_url, json=payload)

        if response.status_code == 201:
            bot.send_message(
                message.chat.id,
                f"Hello, {first_name}! Your User ID ({user_id}) has been saved to the database.",
                     logging.info(f"User {message.from_user.first_name} ({user_id}) saved /start.")
            )
        else:
            bot.send_message(
                message.chat.id,
                "Hello! There was an error saving your information. Please try again later."
            )
            logging.error(f"Failed to save user: {response.text}")
    except Exception as e:
        logging.error(f"Error handling /start command: {e}")
        bot.send_message(message.chat.id, "Oops! Something went wrong. Please try again.")

@bot.message_handler(commands=["help"])
def handle_help(message):
    try:
        help_text = (
            "Here are the commands you can use:\n"
            "/start - Start the bot and get your User ID\n"
            "/help - Get the list of available commands\n"
            "/info - Get information about this bot\n"
        )
        bot.send_message(message.chat.id, help_text, reply_markup=get_main_menu())
        logging.info(f"User {message.from_user.id} requested /help.")
    except Exception as e:
        logging.error(f"Error handling /help command: {e}")
        bot.send_message(message.chat.id, "Oops! Something went wrong. Please try again.")

@bot.message_handler(commands=["info"])
def handle_info(message):
    try:
        info_text = (
            "This is a sample Telegram bot created for demonstration purposes.\n"
            "Feel free to explore the commands or reach out for support!"
        )
        bot.send_message(message.chat.id, info_text, reply_markup=get_main_menu())
        logging.info(f"User {message.from_user.id} requested /info.")
    except Exception as e:
        logging.error(f"Error handling /info command: {e}")
        bot.send_message(message.chat.id, "Oops! Something went wrong. Please try again.")

# Default Handler for Unknown Messages
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    try:
        bot.send_message(
            message.chat.id,
            "I didn't understand that. Please use the menu below or type /help for assistance.",
            reply_markup=get_main_menu(),
        )
        logging.info(f"User {message.from_user.id} sent an unknown message: {message.text}")
    except Exception as e:
        logging.error(f"Error handling unknown message: {e}")
        bot.send_message(message.chat.id, "Oops! Something went wrong. Please try again.")

# Helper Function: Main Menu
def get_main_menu():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("/start", "/help", "/info")
    return keyboard

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    try:
        webhook_url = f"https://telegrambot-osa9.onrender.com/{TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logging.info(f"Webhook set to {webhook_url}")
        return "Webhook set successfully!", 200
    except Exception as e:
        logging.error(f"Error setting webhook: {e}")
        return "Failed to set webhook.", 500

@app.route("/", methods=["GET"])
def index():
    return "Telegram Bot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
