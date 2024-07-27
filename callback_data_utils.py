from models import Event


def create_register_for_event_callback_data(event: Event) -> str:
    return f'register_for_event_{event.uuid}'


def is_register_for_event_callback_data(callback_data: str) -> bool:
    return callback_data.startswith('register_for_event_')


def extract_uuid_from_register_for_event_callback_data(callback_data: str) -> str:
    if not is_register_for_event_callback_data(callback_data):
        raise ValueError('Invalid callback data')
    return callback_data.removeprefix('register_for_event_')


def create_close_registration_on_event_callback_data(event: Event) -> str:
    return f'close_registration_on_event_{event.uuid}'


def is_close_registration_on_event_callback_data(callback_data: str) -> bool:
    return callback_data.startswith('close_registration_on_event_')


def extract_uuid_from_close_registration_on_event_callback_data(callback_data: str) -> str:
    if not is_close_registration_on_event_callback_data(callback_data):
        raise ValueError('Invalid callback data')
    return callback_data.removeprefix('close_registration_on_event_')
