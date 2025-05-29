from pyrogram import Client, filters
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import re
import requests


client_id = "feef7905dd374fd58ba72e08c0d77e70"
client_secret = "60b4007a8b184727829670e2e0f911ca"

auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

bot = Client

# ---------- Function to Fetch Playlist Info ----------
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


# ---------- Handler ----------
@bot.on_message(filters.text & filters.private)
async def handle_spotify_playlist(client, message):
    text = message.text.strip()

    # Regex to check Spotify playlist link
    spotify_pattern = r"https?://open\.spotify\.com/playlist/[a-zA-Z0-9]+"

    if re.search(spotify_pattern, text):
        await message.reply("⏳ Fetching Spotify playlist info...")

        try:
            image_url, name, songs = get_playlist_info(text)

            # Download thumbnail image to send
            image_data = requests.get(image_url).content
            with open("thumb.jpg", "wb") as f:
                f.write(image_data)

            song_text = "\n".join([f"{i+1}. {song}" for i, song in enumerate(songs)])

            await message.reply_photo(
                photo="thumb.jpg",
                caption=f"🎧 **Playlist**: {name}\n\n🎵 **Songs:**\n{song_text[:4000]}"
            )

        except Exception as e:
            await message.reply(f"⚠️ Error fetching playlist: {e}")
