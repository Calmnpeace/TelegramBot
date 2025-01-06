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

# API URL (replace with your actual ngrok URL or hosted API URL)
API_URL = "https://b2ca-218-111-149-235.ngrok-free.app"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    logging.info("Webhook endpoint hit")
    try:
        json_data = request.get_json()
        logging.info(f"Received update: {json_data}")
        bot.process_new_updates([telebot.types.Update.de_json(json_data)])
        return "OK", 200
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return "Internal Server Error", 500

# Helper Function: Persistent Menu (Inline Keyboard)
def get_main_menu():
    logging.info("Generating main menu keyboard")
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(
        telebot.types.InlineKeyboardButton("View All Products", callback_data="view_all_products"),
        telebot.types.InlineKeyboardButton("Add New Data", callback_data="add_new_data")
    )
    keyboard.add(
        telebot.types.InlineKeyboardButton("Update Data", callback_data="update_data"),
        telebot.types.InlineKeyboardButton("Delete Data", callback_data="delete_data")
    )
    keyboard.add(
        telebot.types.InlineKeyboardButton("Get Product by ID", callback_data="get_product_by_id"),
        telebot.types.InlineKeyboardButton("View My Products", callback_data="view_my_products")
    )
    keyboard.add(
        telebot.types.InlineKeyboardButton("Help", callback_data="help"),
        telebot.types.InlineKeyboardButton("Info", callback_data="info")
    )
    return keyboard

@bot.message_handler(commands=["start"])
def handle_start(message):
    logging.info(f"Handling /start command from user {message.from_user.id}")
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    # Prompt user to select a role
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("User", "Admin", "Moderator")
    msg = bot.send_message(
        message.chat.id,
        f"Hello, {first_name}! Welcome to the Mother Database Management System.\n"
        "Please select your role to proceed:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_role_selection)

def process_role_selection(message):
    role = message.text.strip()
    user_id = message.from_user.id
    logging.info(f"User {user_id} selected role: {role}")

    if role.lower() == "user":
        assign_role(user_id, role)
        bot.send_message(
            message.chat.id,
            "You have been assigned the 'User' role. Use the menu below to manage your data.",
            reply_markup=get_main_menu()
        )
    else:
        # Prompt for additional credentials
        msg = bot.reply_to(message, f"As a {role}, please provide your credentials (e.g., admin passcode):")
        bot.register_next_step_handler(msg, verify_credentials, role)

def verify_credentials(message, role):
    user_input = message.text.strip()
    user_id = message.from_user.id
    logging.info(f"Verifying credentials for user {user_id} for role {role}")

    # Example verification logic (replace with actual verification)
    if role.lower() == "admin" and user_input == "admin_passcode":
        assign_role(user_id, role)
        bot.send_message(
            message.chat.id,
            f"Your credentials are verified. You have been assigned the '{role}' role.",
            reply_markup=get_main_menu()
        )
    elif role.lower() == "moderator" and user_input == "moderator_passcode":
        assign_role(user_id, role)
        bot.send_message(
            message.chat.id,
            f"Your credentials are verified. You have been assigned the '{role}' role.",
            reply_markup=get_main_menu()
        )
    else:
        bot.send_message(
            message.chat.id,
            "Invalid credentials. Please try again.",
            reply_markup=get_main_menu()
        )

def assign_role(user_id, role):
    # Logic to save role to the database (mock implementation)
    logging.info(f"Assigning role {role} to user {user_id}")
    # Replace this with actual database interaction code

@bot.message_handler(commands=["help"])
def handle_help(message):
    help_text = (
        "🛠️ **Bot Commands**:\n"
        "/start - Initialize your account.\n"
        "/help - Show this help message.\n"
        "/info - Get information about this bot.\n\n"
        "🎛️ **Menu Options**:\n"
        "1. **View All Products** - View all the stored data.\n"
        "2. **Add New Data** - Add new data to your account.\n"
        "3. **Update Data** - Update an existing data entry.\n"
        "4. **Delete Data** - Delete an existing data entry.\n"
        "5. **Get Product by ID** - Fetch a single product by its ID.\n"
        "6. **View My Products** - View all the data stored by you.\n\n"
        "💡 **Usage Tips**:\n"
        "- Use the provided menu for easy navigation.\n"
        "- Ensure all inputs are in the correct format (e.g., `<name>,<category>,<price>`)."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown", reply_markup=get_main_menu())

@bot.message_handler(commands=["info"])
def handle_info(message):
    info_text = (
        "🤖 **Bot Information**:\n"
        "This bot is designed to help you manage your data efficiently via an interactive Telegram interface. "
        "It allows you to view, add, update, and delete data securely.\n\n"
        "📡 **Powered By**:\n"
        "- Flask Web Framework\n"
        "- Telebot Library for Telegram Integration\n"
        "- A Backend API for Data Management\n\n"
        "🔗 **Developer**:\n"
        "Created by [Your Name]. For queries or issues, contact: [Your Contact Info]."
    )
    bot.send_message(message.chat.id, info_text, parse_mode="Markdown", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True)  # Catches any unrecognized command or input
def handle_unknown_command(message):
    bot.send_message(
        message.chat.id,
        f"🚫 Sorry, I didn't understand that command.\n"
        "Type /help to see the list of available commands or use the menu options below.",
        reply_markup=get_main_menu()
    )

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    try:
        webhook_url = f"https://telegrambot-ckm4.onrender.com/{TOKEN}"  # Replace with your hosted domain
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logging.info(f"Webhook set to {webhook_url}")
        return "Webhook set successfully!", 200
    except Exception as e:
        logging.error(f"Error setting webhook: {e}")
        return "Failed to set webhook.", 500

@app.route("/", methods=["GET"])
def index():
    logging.info("Root endpoint hit - bot is running")
    return "Telegram Bot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port)
