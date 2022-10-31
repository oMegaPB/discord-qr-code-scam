class Messages:
    HEARTBEAT = 'heartbeat'
    HELLO = 'hello'
    INIT = 'init'
    NONCE_PROOF = 'nonce_proof'
    PENDING_REMOTE_INIT = 'pending_remote_init'
    PENDING_TICKET = 'pending_ticket'
    PENDING_LOGIN = 'pending_login'

class DiscordUser:
    def __init__(self, **values):
        self.id = values.get('id')
        self.username = values.get('username')
        self.discrim = values.get('discrim')
        self.avatar_hash = values.get('avatar_hash')
        self.token = values.get('token')

    @classmethod
    def from_payload(cls, payload: str):
        values = payload.split(':')
        return cls(id=values[0],
                   discrim=values[1],
                   avatar_hash=values[2],
                   username=values[3])

    def pretty_print(self):
        out = ''
        out += f'User:            {self.username}#{self.discrim} ({self.id})\n'
        out += f'Avatar URL:      https://cdn.discordapp.com/avatars/{self.id}/{self.avatar_hash}.png\n'
        out += f'Token: {self.token}\n'
        return out