from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import re
import requests
import math
from urllib.parse import urlparse

client_id = "feef7905dd374fd58ba72e08c0d77e70"
client_secret = "60b4007a8b184727829670e2e0f911ca"
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

song_cache = {}  # Stores {message_id: {"songs": [], "ids": []}}

# --- Get Playlist Info ---
def get_playlist_info(playlist_url):
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    playlist = sp.playlist(playlist_id)

    image_url = playlist['images'][0]['url']
    playlist_name = playlist['name']

    song_list = []
    track_ids = []

    for item in playlist['tracks']['items']:
        track = item['track']
        if not track:  # skip if track info is missing
            continue
        name = track['name']
        artist = track['artists'][0]['name']
        track_id = track['id']
        if name and artist and track_id:
            song_list.append(f"{name} - {artist}")
            track_ids.append(track_id)

    return image_url, playlist_name, song_list, track_ids

# --- Generate Pagination Keyboard ---
def generate_keyboard(song_list, page=0, per_page=8):
    start = page * per_page
    end = start + per_page
    buttons = []

    for i, song in enumerate(song_list[start:end], start=start + 1):
        buttons.append([InlineKeyboardButton(text=f"{i}. {song}", callback_data="noop")])

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

# --- Handle Spotify Playlist URL ---
@Client.on_message(filters.private & filters.text)
async def handle_spotify_playlist(client, message):
    text = message.text.strip()
    spotify_pattern = r"https?://open\.spotify\.com/playlist/[a-zA-Z0-9]+"

    if re.search(spotify_pattern, text):
        info_msg = await message.reply("⏳ Fetching Spotify playlist info...")

        try:
            image_url, name, songs, track_ids = get_playlist_info(text)

            # Download playlist image
            image_data = requests.get(image_url).content
            with open("thumb.jpg", "wb") as f:
                f.write(image_data)

            keyboard = generate_keyboard(songs, page=0)

            reply = await message.reply_photo(
                photo="thumb.jpg",
                caption=f"🎧 **Playlist**: {name}\n📀 Total Songs: {len(songs)}\n\n🎵 Select a song below:",
                reply_markup=keyboard
            )

            # Save in cache
            song_cache[reply.id] = {"songs": songs, "ids": track_ids}

            await info_msg.delete()

        except Exception as e:
            await info_msg.edit(f"⚠️ Error: {e}")

# --- Handle Pagination Buttons ---
@Client.on_callback_query(filters.regex("page:"))
async def paginate_callback(client, callback_query):
    page = int(callback_query.data.split(":")[1])
    message_id = callback_query.message.id

    cache = song_cache.get(message_id)
    if not cache:
        await callback_query.answer("❌ Song list expired.", show_alert=True)
        return

    songs = cache["songs"]
    keyboard = generate_keyboard(songs, page=page)
    await callback_query.edit_message_reply_markup(reply_markup=keyboard)

# --- Dummy Buttons (No action) ---
@Client.on_callback_query(filters.regex("noop"))
async def handle_noop(client, callback_query):
    await callback_query.answer("🎵 Downloading soon...", show_alert=False)

# --- Extract Track Info (Helper) ---
def extract_track_info(spotify_url: str):
    parsed = urlparse(spotify_url)
    if "track" not in parsed.path:
        return None

    track_id = parsed.path.split("/")[-1]
    result = sp.track(track_id)

    title = result['name']
    artist = result['artists'][0]['name']
    return title.lower(), artist.lower()
