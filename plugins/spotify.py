from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import re
import requests
import math
from urllib.parse import urlparse
from info import USERBOT_CHAT_ID
import logging
import urllib.parse
from utils import safe_filename, download_with_aria2c, get_song_download_url_by_spotify_url, download_thumbnail
import os

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

logger = logging

client_id = "feef7905dd374fd58ba72e08c0d77e70"
client_secret = "60b4007a8b184727829670e2e0f911ca"
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

song_cache = {}


output_dir = "/downloads"



def extract_track_info(spotify_url: str):
    parsed = urlparse(spotify_url)
    
    if "track" not in parsed.path:
        logging.warning("URL does not contain 'track' in path. Returning None.")
        return None

    track_id = parsed.path.split("/")[-1].split("?")[0]
    try:
        result = sp.track(track_id)
    except Exception as e:
        logging.error(f"Error fetching track info from Spotify API: {e}")
        return None

    title = result['name']
    artist = result['artists'][0]['name']

    # Extract album image (take first image)
    album_images = result['album'].get('images', [])
    image_url = album_images[0]['url'] if album_images else None

    return title, artist, image_url

def get_playlist_info(playlist_url):
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    playlist = sp.playlist(playlist_id)

    image_url = playlist['images'][0]['url']
    playlist_name = playlist['name']

    song_list = []
    track_ids = []

    for item in playlist['tracks']['items']:
        track = item['track']
        name = track['name']
        artist = track['artists'][0]['name']
        track_id = track['id']
        song_list.append(f"{name} - {artist}")
        track_ids.append(track_id)

    return image_url, playlist_name, song_list, track_ids

# --- Generate Pagination Buttons ---
def generate_keyboard(song_list, track_ids, page=0, per_page=8):
    start = page * per_page
    end = start + per_page
    buttons = []

    for i in range(start, min(end, len(song_list))):
        buttons.append([
            InlineKeyboardButton(
                text=f"{i+1}. {song_list[i]}",
                callback_data=f"trackid:{track_ids[i]}"
            )
        ])

    total_pages = math.ceil(len(song_list) / per_page)
    nav_buttons = []

    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page:{page - 1}"))

    nav_buttons.append(InlineKeyboardButton(f"📄 Page {page + 1}/{total_pages}", callback_data="noop"))

    if end < len(song_list):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(buttons)

# --- Message Handler ---
@Client.on_message(filters.private & filters.text)
async def handle_spotify_playlist(client, message):
    text = message.text.strip()
    spotify_pattern = r"https?://open\.spotify\.com/playlist/[a-zA-Z0-9]+"

    if re.search(spotify_pattern, text):
        await message.reply("⏳ Fetching Spotify playlist info...")

        try:
            image_url, name, songs, track_ids = get_playlist_info(text)

            # Download thumbnail
            image_data = requests.get(image_url).content
            with open("thumb.jpg", "wb") as f:
                f.write(image_data)

            keyboard = generate_keyboard(songs, track_ids, page=0)

            reply = await message.reply_photo(
                photo="thumb.jpg",
                caption=f"🎧 **Playlist**: {name}\n📀 Total Songs: {len(songs)}\n\n🎵 Select a song below:",
                reply_markup=keyboard
            )

            song_cache[reply.id] = {"songs": songs, "track_ids": track_ids}

        except Exception as e:
            await message.reply(f"⚠️ Error: {e}")

# --- Pagination Callback Handler ---
@Client.on_callback_query(filters.regex("page:"))
async def paginate_callback(client, callback_query):
    page = int(callback_query.data.split(":")[1])
    message_id = callback_query.message.id

    data = song_cache.get(message_id)
    if not data:
        await callback_query.answer("❌ Song list expired.", show_alert=True)
        return

    songs = data["songs"]
    track_ids = data["track_ids"]
    keyboard = generate_keyboard(songs, track_ids, page=page)
    await callback_query.edit_message_reply_markup(reply_markup=keyboard)

# --- Dummy Button Handler ---
@Client.on_callback_query(filters.regex("noop"))
async def handle_noop(client, callback_query):
    await callback_query.answer("🎵 Downloading soon...", show_alert=False)


message_map = {}

from pyrogram.types import InputMediaAudio


import aiohttp



@Client.on_callback_query(filters.regex("trackid:"))
async def handle_trackid_click(client, callback_query):
    track_id = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    spotify_url = f"https://open.spotify.com/track/{track_id}"

    await callback_query.answer("🎵 Fetching your song...")

    # ---- Extract title, artist, thumbnail URL from Spotify ----
    title, artist, thumb_url = extract_track_info(spotify_url)

    wait_msg = await client.send_message(user_id, "🔄 Please wait... fetching your song.")

    try:
        song_title, song_url = await get_song_download_url_by_spotify_url(spotify_url)
    except Exception as e:
        await wait_msg.edit("⚠️ An error occurred while fetching the song.")
        return

    if not song_url:
        await wait_msg.edit("❌ Song not found via API.")
        return

    safe_name = safe_filename(song_title) + ".mp3"
    download_path = os.path.join(output_dir, safe_name)

    await wait_msg.edit(f"⬇️ Downloading **{song_title}**...")

    success = await download_with_aria2c(song_url, output_dir, safe_name)
    if not success:
        await wait_msg.edit("❌ Failed to download the song.")
        return

    if not os.path.exists(download_path):
        await wait_msg.edit("❌ Downloaded file not found.")
        return

    # ---- Download the thumbnail using helper ----
    thumb_path = os.path.join(output_dir, safe_filename(song_title) + ".jpg")
    thumb_success = await download_thumbnail(thumb_url, thumb_path)

    # ---- Upload the audio with thumb if available ----
    try:
        await wait_msg.edit(f"📤 Uploading **{song_title}**...")

        if thumb_success and os.path.exists(thumb_path):
            await client.send_audio(
                user_id,
                download_path,
                caption=f"🎵 **{song_title}**\n👤 {artist}",
                thumb=thumb_path,
                title=song_title,
                performer=artist
            )
        else:
            await client.send_audio(
                user_id,
                download_path,
                caption=f"🎵 **{song_title}**\n👤 {artist}",
                title=song_title,
                performer=artist
            )

        await wait_msg.delete()

    except Exception as e:
        await wait_msg.edit("⚠️ Failed to send the song file.")

    finally:
        if os.path.exists(download_path):
            os.remove(download_path)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
