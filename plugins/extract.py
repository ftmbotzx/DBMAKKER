from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
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

    await message.reply("Fetching artist's global songs and albums data, please wait...")

    try:
        # Fetch albums (only albums)
        albums = []
        results_albums = sp.artist_albums(artist_id, album_type='album', limit=50)
        albums.extend(results_albums['items'])
        while results_albums['next']:
            results_albums = sp.next(results_albums)
            albums.extend(results_albums['items'])
        album_ids = set(album['id'] for album in albums)
        total_albums = len(album_ids)
        logger.info(f"Total albums fetched: {total_albums}")

        # Fetch singles (only singles)
        singles = []
        results_singles = sp.artist_albums(artist_id, album_type='single', limit=50)
        singles.extend(results_singles['items'])
        while results_singles['next']:
            results_singles = sp.next(results_singles)
            singles.extend(results_singles['items'])
        single_ids = set(single['id'] for single in singles)
        total_singles = len(single_ids)
        logger.info(f"Total singles fetched: {total_singles}")

        # Get tracks from albums
        album_tracks = set()
        for album_id in album_ids:
            tracks = sp.album_tracks(album_id)
            for track in tracks['items']:
                album_tracks.add(track['id'])
        total_songs_albums = len(album_tracks)
        logger.info(f"Total songs from albums: {total_songs_albums}")

        # Get tracks from singles
        single_tracks = set()
        for single_id in single_ids:
            tracks = sp.album_tracks(single_id)
            for track in tracks['items']:
                single_tracks.add(track['id'])
        total_songs_singles = len(single_tracks)
        logger.info(f"Total songs from singles: {total_songs_singles}")

        # Combine all tracks
        all_tracks = album_tracks.union(single_tracks)
        total_unique_songs = len(all_tracks)
        logger.info(f"Total unique songs (albums + singles): {total_unique_songs}")

        original_count = 0
        non_original_count = 0
        artist_name_lower = sp.artist(artist_id)['name'].lower()

        for track_id in all_tracks:
            track = sp.track(track_id)
            artists = [artist['name'].lower() for artist in track['artists']]
            main_artist = artists[0]

            if artist_name_lower in artists:
                if main_artist == artist_name_lower:
                    original_count += 1
                else:
                    non_original_count += 1

        artist_info = sp.artist(artist_id)
        artist_name = artist_info['name']

        reply_text = (
            f"👤 **Artist:** {artist_name}\n\n"
            f"🌏 **Global Albums & Singles Summary:**\n"
            f"• Total Albums: {total_albums}\n"
            f"• Total Singles: {total_singles}\n"
            f"• Total Songs from Albums: {total_songs_albums}\n"
            f"• Total Songs from Singles: {total_songs_singles}\n"
            f"• 🎵 Total Unique Songs (Albums + Singles): {total_unique_songs}\n"
            f"• 🎤 Original Songs (Primary Artist): {original_count}\n"
            f"• 🤝 Other Songs (Featuring/Remix/Collab): {non_original_count}\n"
        )

        logger.info("Final summary prepared and sending reply.")
        await message.reply(reply_text)

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        await message.reply(f"❌ Error occurred: `{e}`")
