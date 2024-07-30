from datetime import datetime

import datetime_utils


class UserModel:
    def __init__(self,
                 id: int,
                 username: str,
                 first_name: str,
                 last_name: str,
                 ):
        self.id = id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name

    def get_full_name(self) -> str:
        if self.last_name:
            return f'{self.first_name} {self.last_name}'
        return self.first_name


class Event:
    def __init__(self,
                 uuid: str,
                 start_time_utc: datetime,
                 description: str,
                 image_id: str | None,
                 is_registration_opened: bool,
                 ):
        self.uuid = uuid
        self.start_time_utc = start_time_utc
        self.description = description
        self.image_id = image_id
        self.is_registration_opened = is_registration_opened

    def get_start_time_moscow_tz(self) -> datetime:
        return datetime_utils.with_zone_same_instant(
            datetime_obj=self.start_time_utc,
            timezone_to=datetime_utils.get_moscow_zone()
        )


class AdministratorState: pass


class AdministratorStateDefault(AdministratorState): pass


class AdministratorStateWaitingForEventDateTime(AdministratorState): pass


class AdministratorStateWaitingForEventDescription(AdministratorState):
    def __init__(self, event_time_utc: datetime):
        self.event_time_utc = event_time_utc


class AdministratorStateFinalConfirmation(AdministratorState):
    def __init__(self, event_time_utc: datetime, event_description: str, image_id: str | None):
        self.event_time_utc = event_time_utc
        self.event_description = event_description
        self.image_id = image_id
