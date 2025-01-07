from flask import Flask, request
import telebot
import os
import logging
import requests
from telebot.types import ReplyKeyboardRemove

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
API_URL = "https://2f8c-218-111-149-235.ngrok-free.app"

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

def get_main_menu(role):
    """
    Generates a main menu inline keyboard dynamically based on the user's role.
    :param role: The role of the user (e.g., 'admin', 'moderator', 'user').
    :return: InlineKeyboardMarkup object with buttons tailored to the user's role.
    """
    logging.info(f"Generating main menu keyboard for role: {role}")
    keyboard = telebot.types.InlineKeyboardMarkup()

    # Admin-specific menu options
    if role == "Admin":
        keyboard.add(
            telebot.types.InlineKeyboardButton("View All Products", callback_data="view_all_products"),
            telebot.types.InlineKeyboardButton("Add New Product", callback_data="add_new_product"),
            telebot.types.InlineKeyboardButton("Update Product", callback_data="update_product"),
            telebot.types.InlineKeyboardButton("Delete Product", callback_data="delete_product"),
        )
        keyboard.add(
            telebot.types.InlineKeyboardButton("View All Orders", callback_data="view_all_orders"),
            telebot.types.InlineKeyboardButton("Delete Orders", callback_data="delete_orders"),
        )

    # Moderator-specific menu options
    elif role == "Moderator":
        keyboard.add(
            telebot.types.InlineKeyboardButton("View All Products", callback_data="view_all_products"),
            telebot.types.InlineKeyboardButton("Add New Product", callback_data="add_new_product"),
            telebot.types.InlineKeyboardButton("Update Product", callback_data="update_product"),
        )
        keyboard.add(
            telebot.types.InlineKeyboardButton("View My Orders", callback_data="view_my_orders"),
        )

    # User-specific menu options
    elif role == "User":
        keyboard.add(
            telebot.types.InlineKeyboardButton("View All Products", callback_data="view_all_products"),
            telebot.types.InlineKeyboardButton("View My Products", callback_data="view_my_products"),
        )
        keyboard.add(
            telebot.types.InlineKeyboardButton("Place an Order", callback_data="place_order"),
            telebot.types.InlineKeyboardButton("View My Orders", callback_data="view_my_orders"),
        )

    else :
        bot.send_message(
            role.chat.id,
            f"You have no role, kindly use '/start' to select role.",
        )
        return None

    # Common options for all roles
    keyboard.add(
        telebot.types.InlineKeyboardButton("Start", callback_data="start"),
        telebot.types.InlineKeyboardButton("Help", callback_data="help"),
        telebot.types.InlineKeyboardButton("Info", callback_data="info")
    )

    return keyboard


# Check if user exists and fetch their role
def check_user_role(chat_id):
    try:
        response = requests.get(f"{API_URL}/users/check/{chat_id}")
        if response.status_code == 200:
            return response.json()["role"]  # Return the role if the user exists
        else:
            logging.warning(f"User not found: {chat_id}")
            return None
    except Exception as e:
        logging.error(f"Error checking user existence: {e}")
        return None


# Process role selection in the bot
@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.from_user.id
    logging.info(f"Handling /start command from user {chat_id}")

    # Check if the user already has a role
    existing_role = check_user_role(chat_id)

    if existing_role:
        # If the user already has a role, show the corresponding menu
        keyboard = get_main_menu(existing_role)
        if keyboard:
            bot.send_message(
                chat_id,
                f"Welcome back! You already have the role '{existing_role}'. Here is your menu:",
                reply_markup=keyboard
            )
        else:
            bot.send_message(chat_id, "Error: Unable to generate menu. Please contact support.")
    else:
        # If no role exists, ask the user to select a role
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("User", "Admin", "Moderator")
        msg = bot.send_message(
            chat_id,
            "Hello! Welcome to the Mother Database Management System.\n"
            "Please select your role to proceed:",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_role_selection)
        ReplyKeyboardRemove()

# Function to call the ngrok API to assign a role
def assign_role_via_api(username, chat_id, new_role):
    url = f"{API_URL}/users/add"
    payload = {
        "username" : username,
        "chat_id": chat_id,  # Admin user who is assigning the role
        "role": new_role,  # The new role to be assigned
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True  # Role successfully assigned
        else:
            logging.error(f"Failed to assign role: {response.json()['error']}")
            return False  # Failed to assign role
    except Exception as e:
        logging.error(f"Error calling the assign role API: {e}")
        return False

# Process role selection from user input
def process_role_selection(message):
    role = message.text.strip()
    chat_id = message.from_user.id
    username = message.from_user.username
    logging.info(f"User {chat_id} selected role: {role}")

    if role.lower() not in ["user", "admin", "moderator"]:
        bot.send_message(
            chat_id,
            "Invalid role selected. Please try again.",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        return

    # Assign the role via the API
    success = assign_role_via_api(username, chat_id, role)
    if success:
        bot.send_message(
            chat_id,
            f"You have been assigned the '{role}' role. Here is your menu:",
            reply_markup=get_main_menu(role)
        )
    else:
        bot.send_message(
            chat_id,
            "Failed to assign role. Please try again or contact support."
        )

# Verify user credentials before assigning admin or moderator roles
def verify_credentials(message, role):
    username = message.from_user.username
    user_input = message.text.strip()
    chat_id = message.from_user.id
    logging.info(f"Verifying credentials for user {chat_id} as {role}")

    # Example verification logic
    if (role.lower() == "admin" and user_input == "admin_passcode") or \
            (role.lower() == "moderator" and user_input == "moderator_passcode"):
        # Assign role using the API
        success = assign_role_via_api(username, chat_id, role)
        if success:
            bot.send_message(
                message.chat.id,
                f"Your credentials are verified. You are now assigned the '{role}' role.",
                reply_markup=get_main_menu(role)
            )
        else:
            bot.send_message(
                message.chat.id,
                "Failed to assign role. Please contact support."
            )
    else:
        bot.send_message(
            message.chat.id,
            "Invalid credentials. Please try again.",
            reply_markup=get_main_menu(role)
        )

@bot.message_handler(func=lambda message: True)  # Catches any unrecognized command or input
def handle_unknown_command(message):
    chat_id = message.from_user.id
    role = check_user_role(chat_id)

    if role:
        keyboard = get_main_menu(role)
        if keyboard:
            bot.send_message(
                chat_id,
                "Please use the menu options below to interact with the system.",
                reply_markup=keyboard
            )
        else:
            bot.send_message(
                chat_id,
                "Error: Unable to generate menu. Please contact support."
            )
    else:
        bot.send_message(
            chat_id,
            "You have not registered a role yet. Use /start to register your role."
        )

@bot.message_handler(func=lambda call:True)
def handle_help(call):
    chat_id = call.from_user.id
    existing_role = check_user_role(chat_id)
    if call.data == "help":
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
        bot.send_message(call.chat.id, help_text, parse_mode="Markdown", reply_markup=get_main_menu(existing_role))

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
    bot.send_message(message.chat.id, info_text, parse_mode="Markdown", reply_markup=get_main_menu(''))

@bot.message_handler(func=lambda message: True)  # Catches any unrecognized command or input
def handle_unknown_command(message):
    bot.send_message(
        message.chat.id,
        f"🚫 Sorry, I didn't understand that command.\n"
        "Type /help to see the list of available commands or use the menu options below.",
        reply_markup=get_main_menu('')
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
