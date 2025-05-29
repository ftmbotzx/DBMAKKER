import os
import logging
import asyncio
import importlib
from collections import deque
from asyncio import Queue
import random

import pytz
from datetime import date, datetime
from aiohttp import web
from pyrogram import Client, __version__, filters, types, utils as pyroutils
from pyrogram.raw.all import layer

from plugins import web_server
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, PORT, USER_SESSION, ADMINS
from plugins.spotify import extract_track_info

# Logging setup
logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# Adjust Pyrogram chat ID ranges
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

# Message Queue Setup
queue = deque()
processing = False
message_map = {}

# ------------------ Bot Class ------------------ #
class Bot(Client):
    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=200,
            plugins={"root": "plugins"},
            sleep_threshold=10,
        )
        self.insta = None

    async def start(self):
        await super().start()
        me = await self.get_me()
        logging.info(f"🤖 {me.first_name} (@{me.username}) running on Pyrogram v{__version__} (Layer {layer})")
        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        time = now.strftime("%H:%M:%S %p")
        await self.send_message(chat_id=LOG_CHANNEL, text=f"✅ Bot Restarted! 📅 Date: {today} 🕒 Time: {time}")
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()
        logging.info(f"🌐 Web Server Running on PORT {PORT}")

    async def stop(self, *args):
        await super().stop()
        logging.info("🛑 Bot Stopped.")


# ------------------ Userbot Class ------------------ #
class Userbot(Client):
    def __init__(self):
        super().__init__(
            name="userbot",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=USER_SESSION,
            plugins={"root": "plugins"},
            workers=50,
        )


app = Bot()
userbot = Userbot()
spotify_bot = "@SpotSeekBot"


from pyrogram.errors import UserNotParticipant


response_queue = Queue()  # Shared queue to hold bot responses

expected_tracks = {}

@userbot.on_message(filters.private & filters.incoming & filters.text)
async def handle_spotify_request(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    if "open.spotify.com/playlist" in text or "track" in text:
        # Generate unique request ID for each incoming request
        request_id = str(uuid.uuid4())

        # Fetch title/artist from Spotify API before forwarding (optional, depends on your logic)
        # For example:
        # title, artist = get_spotify_track_info(text)
        # For demo, dummy values:
        title, artist = "expected title", "expected artist"

        # Save to expected_tracks with unique key
        expected_tracks[(user_id, request_id)] = {"title": title.lower(), "artist": artist.lower()}

        await client.send_message(user_id, "🎧 Sending your link to Spotify bot...")

        # Send message to Spotify bot
        await client.send_message(spotify_bot, text)

@userbot.on_message(filters.chat(spotify_bot))
async def handle_spotify_response(client, message):
    to_delete = []
    for (user_id, request_id), info in expected_tracks.items():
        expected_title = info["title"]
        expected_artist = info["artist"]

        if message.audio:
            audio_title = (message.audio.title or "").lower()
            performer = (message.audio.performer or "").lower()
            caption = (message.caption or "").lower()

            match = (
                expected_title in audio_title or
                expected_artist in performer or
                expected_title in caption
            )

            if match:
                try:
                    await client.send_audio(
                        chat_id=user_id,
                        audio=message.audio.file_id,
                        caption=message.caption or "",
                        title=message.audio.title,
                        performer=message.audio.performer,
                        reply_markup=message.reply_markup
                    )
                    to_delete.append((user_id, request_id))  # Mark for deletion
                except Exception as e:
                    await client.send_message(user_id, f"⚠️ Error: {e}")

    for key in to_delete:
        expected_tracks.pop(key, None)

# ------------------ Startup Main ------------------ #
async def main():
    await app.start()
    logging.info("✅ Bot client started.")

    await userbot.start()
    logging.info(f"👤 Userbot: {(await userbot.get_me()).first_name}")

    for file in os.listdir("./plugins"):
        if file.endswith(".py"):
            importlib.import_module(f"plugins.{file[:-3]}")

    await asyncio.Event().wait()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main()) 
