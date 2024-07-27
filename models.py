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
                 description: str,
                 is_registration_opened: bool,
                 ):
        self.uuid = uuid
        self.description = description
        self.is_registration_opened = is_registration_opened
