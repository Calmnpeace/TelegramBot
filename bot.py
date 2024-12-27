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
API_URL = "https://f536-218-111-149-235.ngrok-free.app/products"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json()
        bot.process_new_updates([telebot.types.Update.de_json(json_data)])
        return "OK", 200
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return "Internal Server Error", 500

# Helper Function: Persistent Menu
def get_main_menu():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("View My Data", "Add New Data")
    keyboard.row("Update Data", "Delete Data")
    keyboard.row("/help", "/info")
    return keyboard

# Command Handlers
@bot.message_handler(commands=["start"])
def handle_start(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name

        # Send data to the API
        payload = {
            "category": "Users",
            "name": first_name,
            "price": 10,
            "quantity": user_id
        }
        response = requests.post(API_URL, json=payload)

        if response.status_code == 201:
            bot.send_message(
                message.chat.id,
                f"Hello, {first_name}! Your User ID ({user_id}) has been saved to the database. Use the menu below to manage your data.",
                reply_markup=get_main_menu()
            )
            logging.info(f"User {first_name} ({user_id}) initialized with /start.")
        else:
            bot.send_message(
                message.chat.id,
                "Hello! There was an error saving your information. Please try again later.",
                reply_markup=get_main_menu()
            )
            logging.error(f"Failed to save user: {response.text}")
    except Exception as e:
        logging.error(f"Error handling /start command: {e}")
        bot.send_message(message.chat.id, "Oops! Something went wrong. Please try again.")

@bot.message_handler(func=lambda message: message.text == "View My Data")
def view_my_data(message):
    try:
        user_id = message.from_user.id
        response = requests.get(f"{API_URL}?user_id={user_id}")
        if response.status_code == 200:
            data = response.json()
            if data:
                result = "\n".join(
                    [f"{d['id']}: {d['name']} - {d['category']} (${d['price']})" for d in data]
                )
                bot.send_message(message.chat.id, f"Your Data:\n{result}", reply_markup=get_main_menu())
            else:
                bot.send_message(message.chat.id, "You have no data.", reply_markup=get_main_menu())
        else:
            bot.send_message(message.chat.id, "Failed to fetch your data.", reply_markup=get_main_menu())
    except Exception as e:
        logging.error(f"Error viewing data: {e}")
        bot.send_message(message.chat.id, "Oops! Something went wrong. Please try again.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: message.text == "Add New Data")
def add_new_data(message):
    msg = bot.reply_to(message, "Provide data as: <name>,<category>,<price>")

    def save_new_data(m):
        try:
            user_id = m.from_user.id
            name, category, price = m.text.split(",")
            payload = {"name": name.strip(), "category": category.strip(), "price": float(price), "quantity": user_id}
            response = requests.post(API_URL, json=payload)
            if response.status_code == 201:
                bot.send_message(m.chat.id, "Data added successfully.", reply_markup=get_main_menu())
            else:
                bot.send_message(m.chat.id, "Failed to add data.", reply_markup=get_main_menu())
        except Exception as e:
            logging.error(f"Error adding data: {e}")
            bot.send_message(m.chat.id, "Invalid input. Please try again.", reply_markup=get_main_menu())

    bot.register_next_step_handler(msg, save_new_data)

@bot.message_handler(func=lambda message: message.text == "Update Data")
def update_data(message):
    msg = bot.reply_to(message, "Provide data as: <id>,<name>,<category>,<price>")

    def save_updated_data(m):
        try:
            user_id = m.from_user.id
            data = m.text.split(",")
            if len(data) != 4:
                bot.send_message(m.chat.id, "Invalid input. Format: <id>,<name>,<category>,<price>", reply_markup=get_main_menu())
                return
            data_id, name, category, price = data
            payload = {"name": name.strip(), "category": category.strip(), "price": float(price), "quantity": user_id}
            response = requests.put(f"{API_URL}/{data_id}", json=payload)
            if response.status_code == 200:
                bot.send_message(m.chat.id, "Data updated successfully.", reply_markup=get_main_menu())
            else:
                bot.send_message(m.chat.id, "Failed to update data.", reply_markup=get_main_menu())
        except Exception as e:
            logging.error(f"Error updating data: {e}")
            bot.send_message(m.chat.id, "Invalid input. Please try again.", reply_markup=get_main_menu())

    bot.register_next_step_handler(msg, save_updated_data)

@bot.message_handler(func=lambda message: message.text == "Delete Data")
def delete_data(message):
    msg = bot.reply_to(message, "Provide the ID of the data to delete.")

    def confirm_delete(m):
        try:
            data_id = m.text
            response = requests.delete(f"{API_URL}/{data_id}")
            if response.status_code == 200:
                bot.send_message(m.chat.id, "Data deleted successfully.", reply_markup=get_main_menu())
            else:
                bot.send_message(m.chat.id, "Failed to delete data. Ensure the ID is correct.", reply_markup=get_main_menu())
        except Exception as e:
            logging.error(f"Error deleting data: {e}")
            bot.send_message(m.chat.id, "Invalid input. Please try again.", reply_markup=get_main_menu())

    bot.register_next_step_handler(msg, confirm_delete)

@bot.message_handler(commands=["help"])
def handle_help(message):
    help_text = (
        "🛠️ **Bot Commands**:\n"
        "/start - Initialize your account.\n"
        "/help - Show this help message.\n"
        "/info - Get information about this bot.\n\n"
        "🎛️ **Menu Options**:\n"
        "1. **View My Data** - View all your stored data.\n"
        "2. **Add New Data** - Add new data to your account.\n"
        "3. **Update Data** - Update an existing data entry.\n"
        "4. **Delete Data** - Delete an existing data entry.\n"
        "5. **Get Product by ID** - Fetch a single product by its ID.\n\n"
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

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    try:
        webhook_url = f"https://telegrambot-osa9.onrender.com/{TOKEN}"  # Replace with your hosted domain
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
