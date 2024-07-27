import logging

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, User, Chat

import callback_data_utils
import constants
import environment_utils
import utils
from database import Database
from models import Event, UserModel

logging.basicConfig(filename='standup.log', encoding='utf-8', level=logging.INFO)

bot = telebot.TeleBot(environment_utils.get_bot_token())
target_chat_id = environment_utils.get_target_chat_id()
administrators = environment_utils.get_admin_accounts_ids()

database = Database()


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Это бот для стендапа.')


@bot.message_handler(commands=['create_event'])
def on_create_event_command(message):
    user = message.from_user
    if not is_administrator(user=user):
        return
    if not is_private_chat(chat=message.chat):
        bot.send_message(
            message.chat.id,
            'Создать событие можно только в личных сообщениях.'
        )
        return

    bot.send_message(
        message.chat.id,
        'Для создания события отправь карточку мероприятия следующим сообщением. Оно будет переслано в общую группу.'
    )
    database.set_is_in_creation_event_state(user_id=message.from_user.id, in_creation_state=True)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    try:
        if callback_data_utils.is_register_for_event_callback_data(call.data):
            event_uuid = callback_data_utils.extract_uuid_from_register_for_event_callback_data(call.data)
            event = database.find_event_by_uuid(uuid=event_uuid)
            if event is None:
                bot.send_message(chat_id=chat_id, text='Мероприятие не найдено :(')
                return

            if not event.is_registration_opened:
                bot.send_message(chat_id=chat_id, text='Регистрация уже закрыта!')
                return

            user = create_user_model(call.from_user)
            if database.is_registered_on_event(user_id=user.id, event_uuid=event_uuid):
                # Уже зарегистрирован, игнорируем повторный клик по кнопке.
                return

            database.register_user_for_event(
                user=user,
                event_uuid=event_uuid
            )
            bot.send_message(chat_id=chat_id, text=f'{user.get_full_name()} ({user.username}) зарегистрировался')

        elif callback_data_utils.is_close_registration_on_event_callback_data(call.data):
            event_uuid = callback_data_utils.extract_uuid_from_close_registration_on_event_callback_data(call.data)
            event = database.find_event_by_uuid(uuid=event_uuid)
            if event is None:
                bot.send_message(chat_id=chat_id, text='Мероприятие не найдено :(')
                return
            if not event.is_registration_opened:
                bot.send_message(chat_id=chat_id, text='Регистрация уже была закрыта ранее')
                return

            database.close_registration(event_uuid=event_uuid)
            bot.send_message(
                chat_id=target_chat_id,
                text='Регистрация на мероприятие закрыта.'
            )

            registered_users = database.get_all_users_registered_for_event(event_uuid=event_uuid)
            if len(registered_users) == 0:
                bot.send_message(chat_id=chat_id, text='Регистрация закрыта! Участников нет.')
                return

            text = 'Регистрация закрыта! Участники: \n\n'
            idx = 1
            for user in registered_users:
                text += f'{idx}. {user.get_full_name()} ({user.username})'
                text += '\n'
                idx += 1
            bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        handle_exception(e=e, user=call.from_user, chat_id=chat_id)


@bot.message_handler(content_types=['text'])
def on_text_messages(message):
    if not database.is_in_creation_event_state(user_id=message.from_user.id):
        bot.send_message(message.chat.id, 'Создать мероприятие можно через команду /create_event')
        return

    event = Event(uuid=utils.generate_uuid(), description=message.text, is_registration_opened=True)
    database.add_new_event(event)
    send_new_event_to_group(event)
    send_new_event_created_confirmation_message(event, message.chat.id)
    database.set_is_in_creation_event_state(user_id=message.from_user.id, in_creation_state=False)


def send_new_event_to_group(event: Event):
    markup = InlineKeyboardMarkup()
    callback_data = callback_data_utils.create_register_for_event_callback_data(event=event)
    markup.add(InlineKeyboardButton('+', callback_data=callback_data))
    bot.send_message(target_chat_id, event.description, reply_markup=markup)


def send_new_event_created_confirmation_message(event: Event, chat_id: int):
    markup = InlineKeyboardMarkup()
    callback_data = callback_data_utils.create_close_registration_on_event_callback_data(event=event)
    markup.add(InlineKeyboardButton('Завершить регистрацию', callback_data=callback_data))
    bot.send_message(chat_id, 'Новое мероприятие создано. Для закрытия записи нажмите на кнопку ниже.', reply_markup=markup)


def create_user_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )


def is_administrator(user: User) -> bool:
    return user.id in administrators


# True если нам пришло сообщение в личке
def is_private_chat(chat: Chat) -> bool:
    return chat.type == 'private'


def handle_exception(e: Exception, user: User, chat_id: int):
    logging.exception(e)
    bot.send_message(chat_id=chat_id, text='Что-то пошло не так, произошла ошибка :(')


if __name__ == '__main__':
    bot.infinity_polling()
