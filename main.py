import os

import telebot

import constants

bot = telebot.TeleBot(os.environ[constants.ENV_BOT_TOKEN])

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Я – бот, который много чего умеет')

if __name__ == '__main__':
    bot.infinity_polling()
