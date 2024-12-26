from flask import Flask, request
import telebot

# Telegram Bot Token
TOKEN = "7557973540:AAGHq6B0tcBSLA49aqaILmwmUTc-JAofMJI"  # Replace with your bot token
bot = telebot.TeleBot(TOKEN)

# Flask app for handling webhooks
app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(json_data)])
    return "OK", 200

@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f"Hello! Your User ID is {user_id}")

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    # Replace YOUR_RENDER_URL with your actual Render service URL
    webhook_url = f"https://telegrambot-osa9.onrender.com"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return "Webhook set successfully!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
