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
import uuid
import re


@userbot.on_message(filters.private & filters.incoming & filters.text)
async def handle_spotify_request(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id not in ADMINS or "open.spotify.com/track" not in text:
        return

    try:
        title, artist = extract_track_info(text)
        await message.reply(f"🔍 Looking for: **{title.title()} - {artist.title()}**")
    except Exception as e:
        await message.reply(f"❌ Failed to fetch track info: {e}")
        return

    # Unique request ID
    request_id = str(uuid.uuid4())

    # Save track info with composite key
    expected_tracks[request_id] = {
        "user_id": user_id,
        "title": title.lower(),
        "artist": artist.lower()
    }

    # Append request ID in message to identify later
    formatted_text = f"{text}\n\n🔑 ID: {request_id}"

    try:
        await client.send_message(spotify_bot, formatted_text)
    except Exception as e:
        await message.reply(f"❌ Couldn't send to Spotify bot: {e}")


@userbot.on_message(filters.chat(spotify_bot))
async def handle_spotify_response(client, message):
    if not message.audio:
        return

    # Try to extract request ID from caption
    caption = (message.caption or "").lower()
    match = re.search(r'id:\s*([a-f0-9-]+)', caption)
    if not match:
        return  # No ID found in caption

    request_id = match.group(1)

    # Check if we have a matching request
    track_info = expected_tracks.get(request_id)
    if not track_info:
        return

    user_id = track_info["user_id"]
    expected_title = track_info["title"]
    expected_artist = track_info["artist"]

    audio_title = (message.audio.title or "").lower()
    performer = (message.audio.performer or "").lower()

    match_found = (
        expected_title in audio_title or
        expected_artist in performer or
        expected_title in caption
    )

    if match_found:
        try:
            await client.send_audio(
                chat_id=user_id,
                audio=message.audio.file_id,
                caption=message.caption or "",
                title=message.audio.title,
                performer=message.audio.performer,
                reply_markup=message.reply_markup
            )
        except Exception as e:
            await client.send_message(user_id, f"⚠️ Error: {e}")
        finally:
            expected_tracks.pop(request_id, None)  # Clean up after send

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
