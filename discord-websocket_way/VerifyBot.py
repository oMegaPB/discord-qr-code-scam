import base64, json, time, asyncio, os, io
import qrcode, aiohttp, discord
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from discord.ext import commands
from assets import Messages, DiscordUser

class DiscordAuthWebsocket:
    WS_ENDPOINT = 'wss://remote-auth-gateway.discord.gg/?v=2'
    LOGIN_ENDPOINT = 'https://discord.com/api/v9/users/@me/remote-auth/login'

    def __init__(self, debug=False):
        self.debug = debug
        self.key = RSA.generate(2048)
        self.cipher = PKCS1_OAEP.new(self.key, hashAlgo=SHA256)
        self.user = None
        self.session: aiohttp.ClientSession = None
        self.loop = asyncio.new_event_loop()
        print("------------------------------------------")
        print("Cipher generated.")

    @property
    def public_key(self):
        pub_key = self.key.publickey().export_key().decode('utf-8')
        pub_key = ''.join(pub_key.split('\n')[1:-1])
        return pub_key

    async def send(self, op, data=None, ws=None):
        payload = {'op': op}
        if data is not None:
            payload.update(**data)
        if self.debug:
            print(f'Send: {payload}')
        await ws.send_json(payload)

    async def exchange_ticket(self, ticket, session: aiohttp.ClientSession):
        print(f'Exch ticket: {ticket}')
        r = await session.post(self.LOGIN_ENDPOINT, json={'ticket': ticket})
        if not r.status == 200:
            return None
        json: dict = await r.json()
        return json.get('encrypted_token')

    def decrypt_payload(self, encrypted_payload):
        payload = base64.b64decode(encrypted_payload)
        decrypted = self.cipher.decrypt(payload)
        return decrypted

    async def get_scanned_user(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        ws = await session.ws_connect(self.WS_ENDPOINT, headers={'Origin': 'https://discord.com'})
        async def heartbeat_sender(ws):
            for _ in range(4):
                if ws.closed:
                    return
                await self.send(Messages.HEARTBEAT, ws=ws)
                await asyncio.sleep(30)
        asyncio.run_coroutine_threadsafe(heartbeat_sender(ws=ws), loop=asyncio.get_running_loop())
        async for message in ws:
            if self.debug:
                print(f'Recv: {message}')
            if type(message.type) in [aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING]:
                break
            data = json.loads(message.data)
            op = data.get('op')
            if op == Messages.HELLO:
                self.heartbeat_interval = data.get('heartbeat_interval') / 1000
                self.last_heartbeat = time.time()
                await self.send(Messages.INIT, {'encoded_public_key': self.public_key}, ws=ws)

            elif op == Messages.NONCE_PROOF:
                nonce = data.get('encrypted_nonce')
                decrypted_nonce = self.decrypt_payload(nonce)
                proof = SHA256.new(data=decrypted_nonce).digest()
                proof = base64.urlsafe_b64encode(proof)
                proof = proof.decode().rstrip('=')
                await self.send(Messages.NONCE_PROOF, {'proof': proof}, ws=ws)

            elif op == Messages.PENDING_REMOTE_INIT:
                fingerprint = data.get('fingerprint')
                img = qrcode.make(f'https://discordapp.com/ra/{fingerprint}')
                factory = io.BytesIO()
                img.save(factory, format='PNG')
                factory.seek(0)
                dfile = discord.File(factory, filename=f'unknown.png')
                await interaction.followup.send("`Prove us that you are not a bot.`", file=dfile, ephemeral=True)

            elif op == Messages.PENDING_TICKET:
                encrypted_payload = data.get('encrypted_user_payload')
                payload = self.decrypt_payload(encrypted_payload)
                self.user = DiscordUser.from_payload(payload.decode())

            elif op == Messages.PENDING_LOGIN:
                ticket = data.get('ticket')
                encrypted_token = await self.exchange_ticket(ticket, session)
                token = self.decrypt_payload(encrypted_token)
                self.user.token = token.decode()
                await interaction.followup.send("`You are successfully verified!`", ephemeral=True)
                await ws.close()
                await session.close()
                return self.user

class VerifBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.auth_ws = DiscordAuthWebsocket(debug=False)
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_scan(self, user: DiscordUser):
        out = '-----------------------------------------------------------------------------------\n'
        out += f'User:            {user.username}#{user.discrim} ({user.id})\n'
        out += f'Avatar URL:      https://cdn.discordapp.com/avatars/{user.id}/{user.avatar_hash}.png\n'
        out += f'Token:           {user.token}'
        print(out)

bot = VerifBot(
    command_prefix="!",
    intents=discord.Intents.all(),
    application_id=931873675454595102
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("------------------------------------------")

@bot.tree.command(name="verify", description="Prove that you're not bot.")
async def verify(interaction: discord.Interaction) -> None:
    user = await bot.auth_ws.get_scanned_user(interaction)
    await bot.on_scan(user)

async def main():
    async with bot:
        await bot.start(os.environ.get("TOKEN_BETA"))
asyncio.new_event_loop().run_until_complete(main())