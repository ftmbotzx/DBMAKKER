from bot import userbot, spotify_bot
from pyrogram import Client, filters
from info import ADMINS
from plugins.spotify import extract_track_info
import uuid

from info import ADMINS
expected_tracks = {}
import uuid
import re

@userbot.on_message(filters.private & filters.incoming & filters.text)
async def handle_spotify_request(client, message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id not in ADMINS or "open.spotify.com" not in text:
        return

    try:
        title, artist = extract_track_info(text)
        await message.reply(f"🔍 Looking for: **{title.title()} - {artist.title()}**")
    except Exception as e:
        await message.reply(f"❌ Failed to fetch track info: {e}")
        return

    # Generate unique request ID for this request
    request_id = str(uuid.uuid4())

    # Save with composite key (user_id, request_id)
    expected_tracks[(user_id, request_id)] = {"title": title.lower(), "artist": artist.lower()}

    try:
        await client.send_message(spotify_bot, text)
    except Exception as e:
        await message.reply(f"❌ Couldn't send to Spotify bot: {e}")

@userbot.on_message(filters.chat(spotify_bot))
async def handle_spotify_response(client, message):
    to_delete = []

    for (user_id, request_id), info in list(expected_tracks.items()):
        expected_title = info["title"]
        expected_artist = info["artist"]

        if message.audio:
            audio_title = (message.audio.title or "").lower()
            performer = (message.audio.performer or "").lower()
            caption = (message.caption or "").lower()

            match = (
                expected_title in audio_title
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

    # Delete matched entries after iterating
    for key in to_delete:
        expected_tracks.pop(key, None)
        
