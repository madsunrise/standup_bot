from models import Event, UserModel


class Database:
    def __init__(self):
        self.is_in_creation_event_state_users = set()
        self.events = set()
        self.registrations = {}

    def set_is_in_creation_event_state(self, user_id: int, in_creation_state: bool):
        if in_creation_state:
            self.is_in_creation_event_state_users.add(user_id)
        else:
            self.is_in_creation_event_state_users.remove(user_id)

    def is_in_creation_event_state(self, user_id: int) -> bool:
        return user_id in self.is_in_creation_event_state_users

    def add_new_event(self, event: Event):
        self.events.add(event)

    def find_event_by_uuid(self, uuid: str) -> Event | None:
        for event in self.events:
            if event.uuid == uuid:
                return event
        return None

    def register_user_for_event(self, user: UserModel, event_uuid: str):
        if event_uuid in self.registrations:
            current_users = self.registrations[event_uuid]
        else:
            current_users = []
        current_users.append(user)
        self.registrations[event_uuid] = current_users

    def is_registered_on_event(self, user_id: int, event_uuid: str) -> bool:
        if event_uuid not in self.registrations:
            return False
        registered_users = self.registrations[event_uuid]
        for user_model in registered_users:
            if user_model.id == user_id:
                return True
        return False

    def get_all_users_registered_for_event(self, event_uuid: str) -> list:
        if event_uuid not in self.registrations:
            return []
        return self.registrations[event_uuid]

    def close_registration(self, event_uuid: str):
        for event in self.events:
            if event.uuid == event_uuid:
                event.is_registration_opened = False
