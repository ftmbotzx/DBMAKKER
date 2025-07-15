from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import logging
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

client_id = "17d04bf5a73040a8926605bfa0daeea3"
client_secret = "7f2af00d12ec4b6ab3dfce13002290d5"
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

    status_msg = await message.reply("⏳ Fetching artist tracks, please wait...")

    try:
        # Albums
        albums = []
        results_albums = sp.artist_albums(artist_id, album_type='album', limit=50)
        albums.extend(results_albums['items'])
        while results_albums['next']:
            results_albums = sp.next(results_albums)
            albums.extend(results_albums['items'])

        # Singles
        singles = []
        results_singles = sp.artist_albums(artist_id, album_type='single', limit=50)
        singles.extend(results_singles['items'])
        while results_singles['next']:
            results_singles = sp.next(results_singles)
            singles.extend(results_singles['items'])

        album_ids = set(album['id'] for album in albums)
        single_ids = set(single['id'] for single in singles)

        all_album_ids = album_ids.union(single_ids)

        logger.info(f"Total releases: {len(all_album_ids)}")

        all_tracks = []

        # Collect all tracks IDs and names
        for release_id in all_album_ids:
            tracks = sp.album_tracks(release_id)
            for track in tracks['items']:
                all_tracks.append((track['id'], track['name']))

        total_tracks = len(all_tracks)
        logger.info(f"Total unique tracks: {total_tracks}")

        # Batch write and send
        batch_size = 100
        batches = [all_tracks[i:i + batch_size] for i in range(0, total_tracks, batch_size)]

        artist_name = sp.artist(artist_id)['name'].replace(" ", "_")
        file_prefix = f"{artist_name}_tracks"

        for index, batch in enumerate(batches, start=1):
            file_name = f"{file_prefix}_part_{index}.txt"

            with open(file_name, "w", encoding="utf-8") as f:
                for track_id, track_name in batch:
                    f.write(f"{track_id} | {track_name}\n")

            await client.send_document(
                chat_id=message.chat.id,
                document=file_name,
                caption=f"✅ Batch {index} ({len(batch)} tracks)"
            )

            logger.info(f"Sent batch {index}")
            await asyncio.sleep(3)  # Wait 3 sec to avoid rate limits

        await status_msg.edit(f"✅ Done! Total tracks: {total_tracks}")

    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit(f"❌ Error: `{e}`")

