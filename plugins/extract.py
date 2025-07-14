from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import logging
import time
from spotipy.exceptions import SpotifyException

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

def safe_spotify_call(func, *args, **kwargs):
    """
    Wrapper to safely call Spotify API with retry on rate limits.
    """
    while True:
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                logger.warning(f"Rate limited by Spotify API. Retrying after {retry_after} seconds...")
                time.sleep(retry_after + 1)
            else:
                raise e

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
        artist_info = safe_spotify_call(sp.artist, artist_id)
        artist_name_lower = artist_info['name'].lower()
        logger.info(f"Artist: {artist_info['name']}")

        # Fetch albums
        albums = []
        results_albums = safe_spotify_call(sp.artist_albums, artist_id, album_type='album', limit=50)
        albums.extend(results_albums['items'])
        logger.info(f"Fetched {len(albums)} albums so far...")
        while results_albums['next']:
            results_albums = safe_spotify_call(sp.next, results_albums)
            albums.extend(results_albums['items'])
            logger.info(f"Fetched {len(albums)} albums so far...")
        album_ids = set(album['id'] for album in albums)
        logger.info(f"Total unique albums fetched: {len(album_ids)}")

        # Fetch singles
        singles = []
        results_singles = safe_spotify_call(sp.artist_albums, artist_id, album_type='single', limit=50)
        singles.extend(results_singles['items'])
        logger.info(f"Fetched {len(singles)} singles so far...")
        while results_singles['next']:
            results_singles = safe_spotify_call(sp.next, results_singles)
            singles.extend(results_singles['items'])
            logger.info(f"Fetched {len(singles)} singles so far...")
        single_ids = set(single['id'] for single in singles)
        logger.info(f"Total unique singles fetched: {len(single_ids)}")

        album_tracks = set()
        single_tracks = set()

        # Fetch tracks in albums with rate limit safe calls
        for idx, album_id in enumerate(album_ids, 1):
            tracks = safe_spotify_call(sp.album_tracks, album_id)
            for track in tracks['items']:
                album_tracks.add(track['id'])
            if idx % 10 == 0:
                logger.info(f"Fetched tracks from {idx}/{len(album_ids)} albums...")
            time.sleep(0.2)  # small delay to reduce rate limit chances

        # Fetch tracks in singles
        for idx, single_id in enumerate(single_ids, 1):
            tracks = safe_spotify_call(sp.album_tracks, single_id)
            for track in tracks['items']:
                single_tracks.add(track['id'])
            if idx % 10 == 0:
                logger.info(f"Fetched tracks from {idx}/{len(single_ids)} singles...")
            time.sleep(0.2)

        all_tracks = album_tracks.union(single_tracks)
        logger.info(f"Total unique tracks from albums and singles combined: {len(all_tracks)}")

        original_count = 0
        non_original_count = 0

        for idx, track_id in enumerate(all_tracks, 1):
            track = safe_spotify_call(sp.track, track_id)
            artists = [a['name'].lower() for a in track['artists']]
            main_artist = artists[0]
            if artist_name_lower in artists:
                if main_artist == artist_name_lower:
                    original_count += 1
                else:
                    non_original_count += 1
            if idx % 50 == 0:
                logger.info(f"Checked {idx}/{len(all_tracks)} tracks for artist roles...")
            time.sleep(0.15)

        total_albums = len(album_ids)
        total_singles = len(single_ids)
        total_album_tracks = len(album_tracks)
        total_single_tracks = len(single_tracks)
        total_songs = len(all_tracks)
        final_total_songs = total_songs  # includes originals + featured + remixes etc

        reply_text = (
            f"👤 **Artist:** {artist_info['name']}\n\n"
            f"📊 **Summary:**\n"
            f"• Total Albums: {total_albums}\n"
            f"• Total Singles: {total_singles}\n"
            f"• Total Songs (Albums): {total_album_tracks}\n"
            f"• Total Songs (Singles): {total_single_tracks}\n"
            f"• Total Unique Songs (Albums + Singles): {total_songs}\n"
            f"• Original Songs (Primary Artist): {original_count}\n"
            f"• Other Songs (Featuring/Remix/Collab): {non_original_count}\n\n"
            f"🎯 **Final Total Songs (All combined):** {final_total_songs}"
        )

        logger.info("Final summary prepared and sending reply.")
        await message.reply(reply_text)

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        await message.reply(f"❌ Error occurred: `{e}`")
