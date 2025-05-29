from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import re
import requests

# --- Spotify API Auth ---
client_id = "feef7905dd374fd58ba72e08c0d77e70"
client_secret = "60b4007a8b184727829670e2e0f911ca"
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

# --- Temporary Song Cache ---
song_cache = {}

# --- Fetch Playlist Info ---
def get_playlist_info(playlist_url):
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    playlist = sp.playlist(playlist_id)

    image_url = playlist['images'][0]['url']
    playlist_name = playlist['name']

    tracks = playlist['tracks']['items']
    song_list = []
    for item in tracks:
        track = item['track']
        name = track['name']
        artist = track['artists'][0]['name']
        song_list.append(f"{name} - {artist}")

    return image_url, playlist_name, song_list

# --- Generate Pagination Buttons ---
def generate_keyboard(song_list, page=0, per_page=8):
    start = page * per_page
    end = start + per_page
    buttons = []

    # Add song buttons (each in a separate row)
    for i, song in enumerate(song_list[start:end], start=1 + start):
        buttons.append([InlineKeyboardButton(text=f"{i}. {song}", callback_data="noop")])

    # Navigation buttons row
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page:{page - 1}"))
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
            image_url, name, songs = get_playlist_info(text)

            # Download thumbnail
            image_data = requests.get(image_url).content
            with open("thumb.jpg", "wb") as f:
                f.write(image_data)

            keyboard = generate_keyboard(songs, page=0)

            # Send photo and save the bot's message ID as key in song_cache
            reply = await message.reply_photo(
                photo="thumb.jpg",
                caption=f"🎧 **Playlist**: {name}\n\n🎵 Select a song below:",
                reply_markup=keyboard
            )

            # Save song list in cache using bot message ID
            song_cache[reply.message_id] = songs

        except Exception as e:
            await message.reply(f"⚠️ Error: {e}")

# --- Pagination Callback Handler ---
@Client.on_callback_query(filters.regex("page:"))
async def paginate_callback(client, callback_query):
    page = int(callback_query.data.split(":")[1])
    message_id = callback_query.message.message_id  # Bot message ID

    songs = song_cache.get(message_id)
    if not songs:
        await callback_query.answer("❌ Song list expired.", show_alert=True)
        return

    keyboard = generate_keyboard(songs, page=page)
    await callback_query.edit_message_reply_markup(reply_markup=keyboard)

# --- Dummy Button Handler ---
@Client.on_callback_query(filters.regex("noop"))
async def handle_noop(client, callback_query):
    await callback_query.answer("🎵 Downloading soon...", show_alert=False)


