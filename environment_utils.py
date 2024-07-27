import os

import constants


def get_bot_token() -> str:
    return os.environ[constants.ENV_BOT_TOKEN]


def get_admin_accounts_ids() -> list:
    value = os.environ[constants.ENV_ADMINISTRATORS_ID]
    if not value:
        return []
    return list(map(lambda x: int(x), value.split(',')))


def get_target_chat_id() -> int:
    return int(os.environ[constants.ENV_TARGET_CHAT_ID])
