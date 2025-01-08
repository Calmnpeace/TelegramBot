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
API_URL = "https://19c7-218-111-149-235.ngrok-free.app"

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
    if role == "Admin" or role == "admin":
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
    elif role == "Moderator" or role == "moderator":
        keyboard.add(
            telebot.types.InlineKeyboardButton("View All Products", callback_data="view_all_products"),
            telebot.types.InlineKeyboardButton("Add New Product", callback_data="add_new_product"),
            telebot.types.InlineKeyboardButton("Update Product", callback_data="update_product"),
        )
        keyboard.add(
            telebot.types.InlineKeyboardButton("View All Orders", callback_data="view_all_orders"),
        )

    # User-specific menu options
    elif role == "User" or role == "user":
        keyboard.add(
            telebot.types.InlineKeyboardButton("View All Products", callback_data="view_all_products"),
        )
        keyboard.add(
            telebot.types.InlineKeyboardButton("Place an Order", callback_data="place_order"),
            telebot.types.InlineKeyboardButton("View My Orders", callback_data="view_all_ordersByUser"),
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
@bot.callback_query_handler(func=lambda call: call.data == "start")
@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.chat.id
    role = check_user_role(chat_id)

    if role:
        # If the user already has a role, show the menu
        bot.send_message(
            chat_id,
            f"Welcome back, {message.from_user.first_name}!\n"
            f"You are logged in as a '{role}'. Here is your menu:",
            reply_markup=get_main_menu(role),
        )
    else:
        # If no role exists, prompt the user to select one
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("User", "Admin", "Moderator")
        msg = bot.send_message(
            chat_id,
            "Hello! Welcome to the Mother Database Management System.\n"
            "Please select your role to proceed:",
            reply_markup=markup,
        )
        bot.register_next_step_handler(msg, process_role_selection)
        ReplyKeyboardRemove()

# Function to call the ngrok API to assign a role
def update_role_via_api(username, chat_id, new_role):
    url = f"{API_URL}/users/add"
    payload = {
        "username": username,
        "chat_id": chat_id,
        "role": new_role
    }
    logging.info(f"Sending payload to API: {payload}")

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True
        else:
            error_message = response.json().get("error", "Unknown error")
            logging.error(f"Failed to update/assign role: {error_message}")
            return False
    except ValueError:
        logging.error("Invalid or empty response from the API.")
        return False
    except Exception as e:
        logging.error(f"Error calling the update role API: {e}")
        return False

# Process role selection from user input
def process_role_selection(message):
    role = message.text.strip()
    chat_id = message.from_user.id
    username = message.from_user.username
    logging.info(f"User {chat_id} selected role: {role}")

    # Check if the role is valid
    if role.lower() not in ["user", "admin", "moderator"]:
        bot.send_message(
            chat_id,
            "Invalid role selected. Please try again.",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        return

    # If Admin or Moderator role is selected, verify credentials
    if role.lower() in ["admin", "moderator"]:
        bot.send_message(
            chat_id,
            f"To verify your credentials for the {role} role, please enter the passcode:"
        )
        bot.register_next_step_handler(message, lambda msg: verify_credentials(msg, role))
        return

    # For "User" role, directly assign without credentials
    success = update_role_via_api(username, chat_id, role)
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

    # Example credential checks (replace with actual logic or API calls)
    if (role.lower() == "admin" and user_input == "admin_passcode") or \
       (role.lower() == "moderator" and user_input == "moderator_passcode"):
        success = update_role_via_api(username, chat_id, role)
        if success:
            bot.send_message(
                chat_id,
                f"Your credentials are verified. You are now assigned the '{role}' role.",
                reply_markup=get_main_menu(role)
            )
        else:
            bot.send_message(
                chat_id,
                "Failed to assign role. Please contact support."
            )
    else:
        bot.send_message(
            chat_id,
            "Invalid credentials. Please try again or contact support."
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

def view_all_products(chat_id):
    try:
        response = requests.get(f"{API_URL}/products")
        if response.status_code == 200:
            products = response.json()
            message = "📦 **All Products**:\n\n"
            for product in products:
                message += f"- ID: {product['id']}\n"
                message += f"  Name: {product['name']}\n"
                message += f"  Description: {product['description']}\n"
                message += f"  Price: {product['price']}\n\n"
            bot.send_message(chat_id, message, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ Failed to fetch products.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {e}")

def add_new_product(chat_id, product_data):
    try:
        response = requests.post(f"{API_URL}/products", json=product_data)
        if response.status_code == 201:
            bot.send_message(chat_id, "✅ Product added successfully.")
        else:
            bot.send_message(chat_id, "❌ Failed to add product.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {e}")

def update_product(chat_id, product_id, updated_data):
    try:
        response = requests.put(f"{API_URL}/products/{product_id}", json=updated_data)
        if response.status_code == 200:
            bot.send_message(chat_id, "✅ Product updated successfully.")
        else:
            bot.send_message(chat_id, "❌ Failed to update product.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {e}")

def delete_product(chat_id, product_id):
    try:
        response = requests.delete(f"{API_URL}/products/{product_id}")
        if response.status_code == 200:
            bot.send_message(chat_id, "✅ Product deleted successfully.")
        else:
            bot.send_message(chat_id, "❌ Failed to delete product.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "update_product")
def handle_update_product(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "Please provide the product ID and the updated details in the format: product_id,name,description,price")
    bot.register_next_step_handler(call.message, process_update_product)

def process_update_product(message):
    chat_id = message.chat.id
    try:
        product_id, name, description, price = message.text.split(",")
        updated_data = {
            "name": name.strip(),
            "description": description.strip(),
            "price": float(price.strip())
        }
        update_product(chat_id, product_id.strip(), updated_data)
    except ValueError:
        bot.send_message(chat_id, "Invalid format. Use: product_id,name,description,price.")

@bot.callback_query_handler(func=lambda call: call.data == "delete_product")
def handle_delete_product(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "Please provide the product ID to delete:")
    bot.register_next_step_handler(call.message, process_delete_product)

def process_delete_product(message):
    chat_id = message.chat.id
    try:
        product_id = message.text.strip()
        delete_product(chat_id, product_id)
    except Exception as e:
        bot.send_message(chat_id, f"Error processing deletion: {e}")

def view_all_orders(message):
    try:
        response = requests.get(f"{API_URL}/orders")
        logging.info(f"API Response Status: {response.status_code}")
        logging.info(f"API Response Content: {response.text}")  # Log the raw response

        if response.status_code == 200:
            orders = response.json()
            logging.info(f"Parsed Orders: {orders}")  # Log the parsed data

            if not orders:  # If no data
                bot.send_message(message.chat.id, "No orders found.")
                return

            message_text = "📋 **All Orders**:\n\n"
            for order in orders:
                message_text += f"- Order ID: {order['id']}\n"
                message_text += f"  Product ID: {order['product_id']}\n"
                message_text += f"  Quantity: {order['quantity']}\n"
                message_text += f"  Order Date: {order['order_date']}\n\n"

            bot.send_message(message.chat.id, message_text, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Failed to fetch orders.")
    except Exception as e:
        logging.error(f"Error in view_all_orders: {e}")
        bot.send_message(message.chat.id, f"⚠️ Error: {e}")

def view_all_ordersByUser(message):
    try:
        id = message.chat.id
        response = requests.get(f"{API_URL}/orders/{id}")
        if response.status_code == 200:
            orders = response.json()
            message = "📋 **All Orders**:\n\n"
            for order in orders:
                message += f"- Order ID: {order['id']}\n"
                message += f"  Product ID: {order['product_id']}\n"
                message += f"  Quantity: {order['quantity']}\n"
                message += f"  Order Date: {order['order_date']}\n\n"
            bot.send_message(message, parse_mode="Markdown")
        else:
            bot.send_message("❌ Failed to fetch orders.")
    except Exception as e:
        bot.send_message( f"⚠️ Error: {e}")

def place_order(chat_id, order_data):
    try:
        response = requests.post(f"{API_URL}/orders", json=order_data)
        if response.status_code == 201:
            bot.send_message(chat_id, "✅ Order placed successfully.")
        else:
            bot.send_message(chat_id, "❌ Failed to place order.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {e}")

def delete_orders(chat_id):
    bot.send_message(chat_id, "Send the Order ID to delete in the format: `/delete_order <order_id>`")

@bot.message_handler(commands=["delete_order"])
def handle_delete_order(message):
    chat_id = message.chat.id
    try:
        order_id = int(message.text.split()[1])
        response = requests.delete(f"{API_URL}/orders/{order_id}")
        if response.status_code == 200:
            bot.send_message(chat_id, f"✅ Order {order_id} deleted successfully.")
        else:
            bot.send_message(chat_id, f"❌ Failed to delete order {order_id}.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "Invalid format. Use: `/delete_order <order_id>`.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.from_user.id
    existing_role = check_user_role(chat_id)

    if not existing_role:
        bot.send_message(chat_id, "You do not have a role assigned. Use /start to register.")
        return

    if call.data == "view_all_products":
        view_all_products(chat_id)
    elif call.data == "add_new_product":
        bot.send_message(chat_id, "Please send product details in the format: name,description,price")
        bot.register_next_step_handler(call.message, handle_add_product)
    elif call.data == "view_all_orders()":
        view_all_orders(call)
    elif call.data == "view_all_ordersByUser":
        view_all_ordersByUser(chat_id)
    elif call.data == "delete_orders":
        delete_orders(chat_id)
    elif call.data == "place_order":
        bot.send_message(chat_id, "Please send order details in the format: product_id,quantity")
        bot.register_next_step_handler(call.message, handle_place_order)
    elif call.data == "start":
        handle_start(call.message)
    elif call.data == "help":
        handle_help(call.message)
    elif call.data == "info":
        handle_info(call.message)

    # Add more handlers as needed

def handle_add_product(message):
    chat_id = message.chat.id
    try:
        name, description, price = message.text.split(",")
        product_data = {"name": name.strip(), "description": description.strip(), "price": float(price.strip()), "created_by": chat_id}
        add_new_product(chat_id, product_data)
    except ValueError:
        bot.send_message(chat_id, "Invalid format. Use: name,description,price.")

def handle_place_order(message):
    chat_id = message.chat.id
    try:
        product_id, quantity = message.text.split(",")
        order_data = {"user_id": chat_id, "product_id": int(product_id.strip()), "quantity": int(quantity.strip())}
        place_order(chat_id, order_data)
    except ValueError:
        bot.send_message(chat_id, "Invalid format. Use: product_id,quantity.")

@bot.callback_query_handler(func=lambda call: call.data == "help")
@bot.message_handler(commands=["help"])
def handle_help(message_or_call):
    # Determine whether the trigger is a message or a callback
    chat_id = message_or_call.message.chat.id if hasattr(message_or_call, "message") else message_or_call.chat.id
    role = check_user_role(chat_id)

    if role:
        help_text = (
            f"🛠️ **Bot Commands for {role}**:\n\n"
            "/start - Initialize your account or reset your role.\n"
            "/help - Show this help message.\n"
            "/info - Get information about this bot.\n\n"
            "🎛️ **Menu Options**:\n"
            "1. **View All Products** - View all products stored in the database.\n"
        )
        if role in ["Admin", "Moderator"]:
            help_text += (
                "2. **Add New Product** - Add a new product to the database.\n"
                "3. **Update Product** - Update an existing product's details.\n"
            )
        if role == "Admin":
            help_text += "4. **Delete Product** - Remove a product from the database.\n"
        if role in ["User", "Moderator", "Admin"]:
            help_text += (
                "5. **Place an Order** - Place an order for a product.\n"
                "6. **View My Orders** - Check your order history.\n"
            )

        bot.send_message(chat_id, help_text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "You do not have a role assigned yet. Use /start to register your role.")

@bot.callback_query_handler(func=lambda call: call.data == "info")
@bot.message_handler(commands=["info"])
def handle_info(message):
    chat_id = message.chat.id
    role = check_user_role(chat_id)

    info_text = (
        "🤖 **Bot Information**:\n\n"
        "This bot is designed to help you manage your database efficiently through an interactive Telegram interface. "
        "You can perform actions such as viewing products, placing orders, and managing data based on your role.\n\n"
        "🔑 **Role-Based Features**:\n"
        "- **Admin**: Full control of products and orders.\n"
        "- **Moderator**: Limited management capabilities.\n"
        "- **User**: Place orders and view products.\n\n"
        "📡 **Powered By**:\n"
        "- Flask Framework\n"
        "- Telebot Library\n"
        "- RESTful API for data operations\n\n"
        "💡 **Developer**:\n"
        "Created by [Your Name]. For queries or issues, contact: [Your Contact Info]."
    )
    bot.send_message(chat_id, info_text, parse_mode="Markdown", reply_markup=get_main_menu(role))

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
