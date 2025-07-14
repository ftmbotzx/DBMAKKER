from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
        await message.reply("Please send artist Spotify link.\nUsage: /ar <artist_spotify_link>")
        return

    artist_url = message.command[1]
    artist_id = extract_artist_id(artist_url)

    if not artist_id:
        await message.reply("Invalid Spotify artist link. Please send a correct link.")
        return

    await message.reply("Fetching detailed song data, please wait...")

    try:
        artist_name_lower = sp.artist(artist_id)['name'].lower()

        # Albums
        albums = []
        results_albums = sp.artist_albums(artist_id, album_type='album', limit=50)
        albums.extend(results_albums['items'])
        while results_albums['next']:
            results_albums = sp.next(results_albums)
            albums.extend(results_albums['items'])
        album_ids = set(album['id'] for album in albums)

        # Singles
        singles = []
        results_singles = sp.artist_albums(artist_id, album_type='single', limit=50)
        singles.extend(results_singles['items'])
        while results_singles['next']:
            results_singles = sp.next(results_singles)
            singles.extend(results_singles['items'])
        single_ids = set(single['id'] for single in singles)

        # Track details holders
        album_tracks = set()
        single_tracks = set()

        # Fetch tracks in albums
        for album_id in album_ids:
            tracks = sp.album_tracks(album_id)
            for track in tracks['items']:
                album_tracks.add(track['id'])

        # Fetch tracks in singles
        for single_id in single_ids:
            tracks = sp.album_tracks(single_id)
            for track in tracks['items']:
                single_tracks.add(track['id'])

        # Combine all tracks (unique)
        all_tracks = album_tracks.union(single_tracks)

        # Count originals and non-originals in all tracks
        original_count = 0
        non_original_count = 0

        for track_id in all_tracks:
            track = sp.track(track_id)
            artists = [a['name'].lower() for a in track['artists']]
            main_artist = artists[0]
            if artist_name_lower in artists:
                if main_artist == artist_name_lower:
                    original_count += 1
                else:
                    non_original_count += 1

        total_songs = len(all_tracks)
        total_album_tracks = len(album_tracks)
        total_single_tracks = len(single_tracks)
        total_albums = len(album_ids)
        total_singles = len(single_ids)

        reply_text = (
            f"👤 **Artist:** {sp.artist(artist_id)['name']}\n\n"
            f"📊 **Summary:**\n"
            f"• Total Albums: {total_albums}\n"
            f"• Total Singles: {total_singles}\n"
            f"• Total Songs (Albums): {total_album_tracks}\n"
            f"• Total Songs (Singles): {total_single_tracks}\n"
            f"• Total Unique Songs (Albums + Singles): {total_songs}\n"
            f"• Original Songs (Primary Artist): {original_count}\n"
            f"• Other Songs (Featuring/Remix/Collab): {non_original_count}\n"
        )

        await message.reply(reply_text)

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        await message.reply(f"❌ Error occurred: `{e}`")
