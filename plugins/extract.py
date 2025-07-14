from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

client_id = "feef7905dd374fd58ba72e08c0d77e70"
client_secret = "60b4007a8b184727829670e2e0f911ca"
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

app = Client

def extract_artist_id(url):
    match = re.search(r"artist/([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None

@app.on_message(filters.command("ar") & filters.private)
async def artist_songs(client, message):
    if len(message.command) < 2:
        await message.reply("Please send artist Spotify link.\nUsage: /artist_songs <artist_spotify_link>")
        return

    artist_url = message.command[1]
    artist_id = extract_artist_id(artist_url)

    if not artist_id:
        await message.reply("Invalid Spotify artist link. Please send a correct link.")
        return

    await message.reply("Fetching artist's songs and albums data for India, please wait...")

    try:
        albums_india = []
        results = sp.artist_albums(artist_id, album_type='album,single', country='IN', limit=50)
        albums_india.extend(results['items'])

        print(f"Fetched {len(albums_india)} India albums so far...")

        while results['next']:
            results = sp.next(results)
            albums_india.extend(results['items'])
            print(f"Fetched {len(albums_india)} India albums so far...")

        india_album_ids = set(album['id'] for album in albums_india)

        track_ids = set()
        for album_id in india_album_ids:
            tracks = sp.album_tracks(album_id)
            for track in tracks['items']:
                track_ids.add(track['id'])

        total_songs_india = len(track_ids)
        total_albums_india = len(india_album_ids)

        # Global albums
        albums_global = []
        results_global = sp.artist_albums(artist_id, album_type='album,single', limit=50)
        albums_global.extend(results_global['items'])

        print(f"Fetched {len(albums_global)} Global albums so far...")

        while results_global['next']:
            results_global = sp.next(results_global)
            albums_global.extend(results_global['items'])
            print(f"Fetched {len(albums_global)} Global albums so far...")

        global_album_ids = set(album['id'] for album in albums_global)
        total_albums_global = len(global_album_ids)

        artist_info = sp.artist(artist_id)
        artist_name = artist_info['name']

        log_info = (
            f"🔍 Log Info:\n"
            f"India Albums Fetched: {total_albums_india}\n"
            f"Global Albums Fetched: {total_albums_global}\n"
            f"Unique Songs in India: {total_songs_india}"
        )

        reply_text = (
            f"👤 **Artist:** {artist_name}\n\n"
            f"🌏 **Total Albums & Singles (Global):** {total_albums_global}\n"
            f"🇮🇳 **Total Albums & Singles (India):** {total_albums_india}\n"
            f"🎵 **Unique Songs in India:** {total_songs_india}\n\n"
            f"{log_info}"
        )

        await message.reply(reply_text)

    except Exception as e:
        await message.reply(f"❌ Error occurred: `{e}`")
