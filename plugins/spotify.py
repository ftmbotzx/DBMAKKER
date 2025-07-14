from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import re
import requests
import math
from urllib.parse import urlparse
import logging
import os
from utils import safe_filename, download_with_aria2c, get_song_download_url_by_spotify_url, download_thumbnail
import random
import time
import asyncio

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

logger = logging

client_id = "feef7905dd374fd58ba72e08c0d77e70"
client_secret = "60b4007a8b184727829670e2e0f911ca"
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

song_cache = {}

output_dir = os.path.join(os.getcwd(), "downloads")
os.makedirs(output_dir, exist_ok=True)


# --- Rate limiting and concurrency control ---

user_request_times = {}  # user_id: list of timestamps
user_locks = {}         # user_id: asyncio.Lock()

def can_user_request(user_id: int) -> bool:
    now = time.time()
    window = 30  # seconds
    max_requests = 2

    times = user_request_times.get(user_id, [])
    # Remove timestamps older than window
    times = [t for t in times if now - t < window]
    user_request_times[user_id] = times

    if len(times) >= max_requests:
        return False
    return True

def add_user_request(user_id: int):
    now = time.time()
    if user_id not in user_request_times:
        user_request_times[user_id] = []
    user_request_times[user_id].append(now)

async def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]


# --- Spotify info extraction functions ---

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


# --- Main Message Handler with rate limiting & concurrency ---

@Client.on_message(filters.private & filters.text)
async def handle_spotify_link(client, message):
    user_id = message.from_user.id

    # Rate limit check
    if not can_user_request(user_id):
        await message.reply("⚠️ You can only make 2 requests every 30 seconds. Please wait before trying again.")
        return

    # Concurrency lock check
    lock = await get_user_lock(user_id)
    if lock.locked():
        await message.reply("⚠️ You already have a request running. Please wait for it to finish.")
        return

    async with lock:
        add_user_request(user_id)

        text = message.text.strip()

        playlist_pattern = r"https?://open\.spotify\.com/playlist/[a-zA-Z0-9]+"
        track_pattern = r"https?://open\.spotify\.com/track/[a-zA-Z0-9]+"

        if re.search(playlist_pattern, text):
            # Handle playlist
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

        elif re.search(track_pattern, text):
            # Handle single track directly
            ansh = await message.reply("⏳ Fetching Spotify track info...")

            track_info = extract_track_info(text)
            if not track_info:
                await message.reply("⚠️ Could not fetch track info. Please check the link.")
                return

            title, artist, thumb_url = track_info

            wait_msg = await message.reply(f"🔄 Please wait... fetching your song: **{title}**")
            await ansh.delete()

            try:
                song_title, song_url = await get_song_download_url_by_spotify_url(text)
            except Exception as e:
                await wait_msg.edit("⚠️ An error occurred while fetching the song.")
                return

            if not song_url:
                await wait_msg.edit("❌ Song not found via API.")
                return

            base_name = safe_filename(song_title)
            unique_number = random.randint(100, 999)
            safe_name = f"{base_name}_{unique_number}.mp3"
            download_path = os.path.join(output_dir, safe_name)


            await wait_msg.edit(f"⬇️ Downloading **{song_title}**...")

            success = await download_with_aria2c(song_url, output_dir, safe_name)
            if not success:
                await wait_msg.edit("❌ Failed to download the song.")
                return

            if not os.path.exists(download_path):
                await wait_msg.edit("❌ Downloaded file not found.")
                return

            # Download thumbnail
            thumb_path = os.path.join(output_dir, safe_filename(song_title) + ".jpg")
            logging.info(f"download path {thumb_path}")
            thumb_success = await download_thumbnail(thumb_url, thumb_path)

            try:
                await wait_msg.edit(f"📤 Uploading **{song_title}**...")

                if thumb_success and os.path.exists(thumb_path):
                    await client.send_audio(
                        message.chat.id,
                        download_path,
                        caption=f"🎵 **{song_title}**\n👤 {artist}",
                        thumb=thumb_path,
                        title=song_title,
                        performer=artist
                    )
                else:
                    await client.send_audio(
                        message.chat.id,
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

        else:
            # If message does not match any Spotify pattern
            pass


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


# --- Track ID Callback Handler with rate limiting & concurrency ---

@Client.on_callback_query(filters.regex("trackid:"))
async def handle_trackid_click(client, callback_query):
    user_id = callback_query.from_user.id

    if not can_user_request(user_id):
        await callback_query.answer("⚠️ Rate limit exceeded: max 2 requests per 30 seconds.", show_alert=True)
        return

    lock = await get_user_lock(user_id)
    if lock.locked():
        await callback_query.answer("⚠️ You already have a request running. Please wait.", show_alert=True)
        return

    async with lock:
        add_user_request(user_id)

        track_id = callback_query.data.split(":")[1]
        spotify_url = f"https://open.spotify.com/track/{track_id}"

        await callback_query.answer("🎵 Fetching your song...")

        # Extract title, artist, thumbnail URL from Spotify
        track_info = extract_track_info(spotify_url)
        if not track_info:
            await client.send_message(user_id, "⚠️ Failed to fetch track info.")
            return

        title, artist, thumb_url = track_info

        wait_msg = await client.send_message(user_id, "🔄 Please wait... fetching your song.")

        try:
            song_title, song_url = await get_song_download_url_by_spotify_url(spotify_url)
        except Exception as e:
            await wait_msg.edit("⚠️ An error occurred while fetching the song.")
            return

        if not song_url:
            await wait_msg.edit("❌ Song not found via API.")
            return

        base_name = safe_filename(song_title)
        unique_number = random.randint(100, 999)
        safe_name = f"{base_name}_{unique_number}.mp3"
        download_path = os.path.join(output_dir, safe_name)


        await wait_msg.edit(f"⬇️ Downloading **{song_title}**...")

        success = await download_with_aria2c(song_url, output_dir, safe_name)
        if not success:
            await wait_msg.edit("❌ Failed to download the song.")
            return

        if not os.path.exists(download_path):
            await wait_msg.edit("❌ Downloaded file not found.")
            return

        # Download the thumbnail
        thumb_path = os.path.join(output_dir, safe_filename(song_title) + ".jpg")
        logging.info(f"download path {thumb_path}")
        thumb_success = await download_thumbnail(thumb_url, thumb_path)

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
