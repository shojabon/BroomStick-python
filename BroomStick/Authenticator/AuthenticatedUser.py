
class AuthenticatedUser:

    def __init__(self, user_id, username, metadata):
        self.user_id = user_id
        self.username = username
        self.metadata = metadata

    def get_user_id(self):
        return self.user_id

    def get_username(self):
        return self.username

    def get_metadata(self):
        return self.metadata