import locale
import logging
import threading
import time

import schedule
from datetime import timedelta, datetime

import pytz
import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, User, Chat

import callback_data_utils
import datetime_utils
import environment_utils
import formatters
import utils
from database import Database
from models import Event, UserModel, AdministratorStateWaitingForEventDateTime, \
    AdministratorStateDefault, AdministratorStateWaitingForEventDescription, AdministratorStateFinalConfirmation

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
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
            'Создать мероприятие можно только в личных сообщениях.'
        )
        return

    one_week_later = datetime_utils.get_moscow_time() + timedelta(days=7)

    bot.send_message(
        message.chat.id,
        f'Для создания мероприятия укажите дату и время мероприятия в формате дд.мм.гггг чч:мм.\n\n'
        f'Например, \"{datetime_utils.to_string(datetime_obj=one_week_later, pattern=formatters.dd_mm_yyyy_hh_mm)}\".',
        reply_markup=create_reset_administrator_state_button(),
    )

    database.set_administrator_state(
        user_id=message.from_user.id,
        state=AdministratorStateWaitingForEventDateTime(),
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        if callback_data_utils.is_register_for_event_callback_data(call.data):
            event_uuid = callback_data_utils.extract_uuid_from_register_for_event_callback_data(call.data)
            event = database.find_event_by_uuid(uuid=event_uuid)
            user = create_user_model(call.from_user)

            if event is None:
                bot.send_message(chat_id=user.id, text='Мероприятие не найдено :(')
                return

            event_time_formatted = datetime_utils.to_string(event.get_start_time_moscow_tz(), formatters.d_mmm_HH_mm)

            if not event.is_registration_opened:
                safe_send_message(
                    chat_id=user.id,
                    text=f'Регистрация на мероприятие {event_time_formatted} уже завершена.'
                )
                return

            if database.is_registered_on_event(user_id=user.id, event_uuid=event_uuid):
                database.unregister_user(user_id=user.id, event_uuid=event_uuid)
                safe_send_message(
                    chat_id=user.id,
                    text=f'Регистрация на мероприятие {event_time_formatted} отменена.'
                )
                return

            database.register_user_for_event(
                user=user,
                event_uuid=event_uuid
            )

            # Может вылететь исключение, т.к. если юзер не запускал бота, то мы не сможем написать ему в личку.
            safe_send_message(
                chat_id=user.id,
                text=f'Ты успешно зарегистрировался на мероприятие {event_time_formatted}'
            )

            notification_text = f'{user.get_full_name()}'
            if user.username is not None:
                notification_text += f' (@{user.username})'

            notification_text += f' зарегистрировался на {event_time_formatted}'
            for admin_id in administrators:
                bot.send_message(
                    chat_id=admin_id,
                    text=notification_text
                )

        elif callback_data_utils.is_close_registration_on_event_callback_data(call.data):
            if not is_administrator(call.from_user):
                return
            event_uuid = callback_data_utils.extract_uuid_from_close_registration_on_event_callback_data(call.data)
            event = database.find_event_by_uuid(uuid=event_uuid)
            if event is None:
                bot.send_message(chat_id=call.message.chat.id, text='Мероприятие не найдено :(')
                return
            if not event.is_registration_opened:
                bot.send_message(chat_id=call.message.chat.id, text='Регистрация уже была закрыта ранее')
                return

            event.is_registration_opened = False
            database.update_event(event=event)

            displayed_event_time = datetime_utils.to_string(event.get_start_time_moscow_tz(), formatters.d_mmm_HH_mm)
            bot.send_message(
                chat_id=target_chat_id,
                text=f'Регистрация на мероприятие {displayed_event_time} закрыта.'
            )

            registered_users = database.get_all_users_registered_for_event(event_uuid=event_uuid)
            if len(registered_users) == 0:
                bot.send_message(chat_id=call.message.chat.id, text='Регистрация закрыта! Участников нет.')
                return

            text = 'Регистрация закрыта! Участники: \n\n'
            idx = 1
            for user in registered_users:
                text += f'{idx}. {user.get_full_name()}'
                if user.username is not None:
                    text += f' (@{user.username})'
                text += '\n'
                idx += 1
            bot.send_message(chat_id=call.message.chat.id, text=text)

        elif callback_data_utils.is_reset_administrator_state_callback_data(call.data):
            if is_administrator(call.from_user):
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                database.reset_administrator_state(user_id=call.from_user.id)

        elif callback_data_utils.is_confirm_event_creation_callback_data(call.data):
            if not is_administrator(call.from_user):
                return
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            current_state = database.get_administrator_state(user_id=call.from_user.id)
            if not isinstance(current_state, AdministratorStateFinalConfirmation):
                bot.send_message(chat_id=call.message.chat.id, text='Что-то пошло не так :/\n\nПовторите попытку.')
                database.reset_administrator_state(user_id=call.from_user.id)
                return

            event = Event(
                uuid=utils.generate_uuid(),
                start_time_utc=current_state.event_time_utc,
                description=current_state.event_description,
                image_id=current_state.image_id,
                is_registration_opened=True,
            )
            send_new_event_to_group(event=event)
            send_new_event_created_confirmation_message(event_uuid=event.uuid, chat_id=call.message.chat.id)
            database.reset_administrator_state(user_id=call.from_user.id)
            database.add_new_event(event)

    except Exception as e:
        handle_exception(e=e, chat_id=call.message.chat.id)


@bot.message_handler(content_types=['text', 'photo'])
def on_text_messages(message):
    user = message.from_user
    if not is_administrator(user=user):
        return

    current_state = database.get_administrator_state(user_id=user.id)
    if isinstance(current_state, AdministratorStateDefault):
        bot.send_message(message.chat.id, 'Создать мероприятие можно через команду /create_event')
        return
    elif isinstance(current_state, AdministratorStateWaitingForEventDateTime):
        try:
            parsed_time = datetime.strptime(message.text, formatters.dd_mm_yyyy_hh_mm)
            parsed_moscow_time = datetime_utils.get_moscow_zone().localize(parsed_time)
            start_time_in_utc = datetime_utils.with_zone_same_instant(
                datetime_obj=parsed_moscow_time,
                timezone_to=pytz.utc
            )

            if datetime.now(tz=pytz.utc) >= start_time_in_utc:
                bot.send_message(message.chat.id, 'Время в прошлом! Повторите попытку.')
                return 

            new_state = AdministratorStateWaitingForEventDescription(event_time_utc=start_time_in_utc)
            database.set_administrator_state(user_id=user.id, state=new_state)
            bot.send_message(
                chat_id=message.chat.id,
                text='Опишите мероприятие одним сообщением, позже оно будет переслано в общую группу. '
                     'Вы также можете прикрепить изображение к сообщению.\n\n'
                     'Также укажите в сообщении дату и время мероприятия, так как оно будет переслано без изменений.',
                reply_markup=create_reset_administrator_state_button(),
            )
        except ValueError:
            bot.send_message(message.chat.id, 'Не удалось распознать время начала мероприятия. Попробуйте ещё раз.')
            return
    elif isinstance(current_state, AdministratorStateWaitingForEventDescription):
        image_id = None
        if message.content_type == 'text':
            event_description = message.text  # просто текстовое сообщение
        elif message.content_type == 'photo':
            event_description = message.caption  # юзер отправил картинку, берём подпись к картинке
            # message.photo – это лист из картинок разных разрешений, а последняя картинка как раз в лучшем качестве.
            image_id = message.photo[-1].file_id
            if event_description is None or len(event_description) == 0:
                bot.send_message(chat_id=message.chat.id, text='Не указана подпись к картинке! Повторите попытку.')
                return
        else:
            raise ValueError('Unknown message content type')

        new_state = AdministratorStateFinalConfirmation(
            event_time_utc=current_state.event_time_utc,
            event_description=event_description,
            image_id=image_id,
        )

        if image_id:
            bot.send_photo(
                chat_id=message.chat.id,
                photo=image_id,
                caption=new_state.event_description
            )
        else:
            bot.send_message(chat_id=message.chat.id, text=new_state.event_description)

        reply_markup = InlineKeyboardMarkup()
        positive_button = InlineKeyboardButton(
            text='Подтвердить',
            callback_data=callback_data_utils.create_confirm_event_creation_callback_data()
        )
        reply_markup.add(positive_button)

        negative_button = InlineKeyboardButton(
            text='Отмена',
            callback_data=callback_data_utils.create_reset_administrator_state_callback_data()
        )
        reply_markup.add(negative_button)
        moscow_time = datetime_utils.with_zone_same_instant(
            datetime_obj=new_state.event_time_utc,
            timezone_to=datetime_utils.get_moscow_zone()
        )
        bot.send_message(
            chat_id=message.chat.id,
            text=f'Дата и время мероприятия: {datetime_utils.to_string(moscow_time, formatters.d_mmm_HH_mm)} (мск).\n\n'
                 f'После подтверждения сообщение выше будет сразу отправлено в общую группу.',
            reply_markup=reply_markup,
        )
        database.set_administrator_state(user_id=user.id, state=new_state)


def send_new_event_to_group(event: Event):
    markup = InlineKeyboardMarkup()
    callback_data = callback_data_utils.create_register_for_event_callback_data(event=event)
    markup.add(InlineKeyboardButton('+', callback_data=callback_data))
    if event.image_id:
        bot.send_photo(
            chat_id=target_chat_id,
            photo=event.image_id,
            caption=event.description,
            reply_markup=markup
        )
    else:
        bot.send_message(
            chat_id=target_chat_id,
            text=event.description,
            reply_markup=markup
        )


def send_new_event_created_confirmation_message(event_uuid: str, chat_id: int):
    markup = InlineKeyboardMarkup()
    callback_data = callback_data_utils.create_close_registration_on_event_callback_data(event_uuid=event_uuid)
    markup.add(InlineKeyboardButton('Завершить регистрацию', callback_data=callback_data))
    bot.send_message(chat_id, 'Новое мероприятие создано. Для закрытия записи нажмите на кнопку ниже.',
                     reply_markup=markup)


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


def handle_exception(e: Exception, chat_id: int):
    logging.exception(e)
    bot.send_message(chat_id=chat_id, text='Что-то пошло не так, произошла ошибка :(')


def create_reset_administrator_state_button() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    callback_data = callback_data_utils.create_reset_administrator_state_callback_data()
    markup.add(InlineKeyboardButton('Отмена', callback_data=callback_data))
    return markup


def safe_send_message(chat_id: int, text: str):
    try:
        bot.send_message(
            chat_id=chat_id,
            text=text
        )
    except ApiTelegramException:
        pass


def run_scheduler():
    schedule.every().hour.do(do_every_hour)
    while True:
        schedule.run_pending()
        time.sleep(1)

def do_every_hour():
    # метод запускается каждый час
    pass

scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.start()

if __name__ == '__main__':
    bot.infinity_polling()
