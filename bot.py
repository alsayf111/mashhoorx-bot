
import telebot
import os

API_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلًا بك في بوت مشهور! تابع التحديثات هنا أول بأول.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "تحليل السوق قادم... ترقب.")

bot.infinity_polling()
