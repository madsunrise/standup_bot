from models import Event, UserModel, AdministratorState, AdministratorStateDefault


class Database:
    def __init__(self):
        self.administrator_state = {}
        self.created_events = set()
        self.registrations = {}

    def get_administrator_state(self, user_id: int) -> AdministratorState:
        if user_id not in self.administrator_state:
            return AdministratorStateDefault()
        return self.administrator_state[user_id]

    def set_administrator_state(self, user_id: int, state: AdministratorState):
        self.administrator_state[user_id] = state

    def reset_administrator_state(self, user_id: int):
        self.administrator_state.pop(user_id, None)

    def add_new_event(self, event: Event):
        self.created_events.add(event)

    def update_event(self, event: Event):
        result = set()
        for item in self.created_events:
            if item.uuid == event.uuid:
                result.add(event)
            else:
                result.add(item)

    def find_event_by_uuid(self, uuid: str) -> Event | None:
        for event in self.created_events:
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

    def unregister_user(self, user_id: int, event_uuid: str):
        if event_uuid not in self.registrations:
            return
        registered_users = self.registrations[event_uuid]
        new_registered_users = []
        for user_model in registered_users:
            if user_model.id != user_id:
                new_registered_users.append(user_model)
        self.registrations[event_uuid] = new_registered_users

    def get_all_users_registered_for_event(self, event_uuid: str) -> list:
        if event_uuid not in self.registrations:
            return []
        return self.registrations[event_uuid]
