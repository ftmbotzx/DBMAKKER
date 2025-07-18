import time
import re
from pyrogram import Client, filters
from spotipy import SpotifyException
import logging
from plugins.spotify_client_manager import SpotifyClientManager  # Import the custom manager

logger = logging.getLogger(__name__)

# Define your multiple Spotify clients
clients = [
    {"client_id": "87c0e80d2698480b8130e1940949e438", "client_secret": "3c58dd0817b04641a4e0a918e4c7fe2c"},
    {"client_id": "8afb35368d464b5ba5615fbaeae7ed20", "client_secret": "f317c8085a81406bb6244c8c3182f283"},
    {"client_id": "46dccaad9e6b46c396bf9d140325c2fb", "client_secret": "3b6b00a5d5454a0888c2098b628ab5f8"},
]

spotify_manager = SpotifyClientManager(clients)

async def safe_spotify_call(endpoint_url, params=None):
    while True:
        response = await spotify_manager.make_request(endpoint_url, params)
        if response is not None:
            return response
        await asyncio.sleep(1)

@Client.on_message(filters.command("artist") & filters.private & filters.reply)
async def artist_bulk_tracsdks(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("❗ Please reply to a .txt file containing artist links.")
        return

    status_msg = await message.reply("📥 Downloading file...")

    file_path = await message.reply_to_message.download()
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    all_tracks = []
    artist_counter = 0

    for line in lines:
        match = re.search(r"spotify\.com/artist/([a-zA-Z0-9]+)", line)
        if not match:
            continue

        artist_id = match.group(1)
        artist_counter += 1

        try:
            logger.info(f"🎤 Fetching albums for Artist {artist_counter}: {artist_id}")
            album_ids = set()

            url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
            params = {"album_type": "album,single", "limit": 50}
            results = await safe_spotify_call(url, params)

            album_ids.update([album['id'] for album in results['items']])

            while results.get('next'):
                url = results['next']
                results = await safe_spotify_call(url)
                album_ids.update([album['id'] for album in results['items']])

            logger.info(f"📀 Total releases: {len(album_ids)}")

            for idx, release_id in enumerate(album_ids, 1):
                try:
                    url = f"https://api.spotify.com/v1/albums/{release_id}/tracks"
                    tracks = await safe_spotify_call(url)
                    all_tracks.extend([track['id'] for track in tracks['items']])
                    await asyncio.sleep(0.2)

                    if idx % 50 == 0:
                        await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"⚠️ Error fetching album {release_id}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"⚠️ Error with artist {artist_id}: {e}")
            await client.send_message(message.chat.id, f"⚠️ Error fetching {artist_id}: {e}")
            continue

        if len(all_tracks) >= 5000:
            batch = all_tracks[:5000]
            all_tracks = all_tracks[5000:]
            part_file = f"tracks_part_{artist_counter}.txt"
            with open(part_file, "w", encoding="utf-8") as f:
                f.write("\n".join(batch))

            await client.send_document(
                chat_id=message.chat.id,
                document=part_file,
                caption=f"✅ Part from Artist #{artist_counter} (5000 tracks)"
            )
            await asyncio.sleep(3)

    if all_tracks:
        part_file = f"tracks_final.txt"
        with open(part_file, "w", encoding="utf-8") as f:
            f.write("\n".join(all_tracks))

        await client.send_document(
            chat_id=message.chat.id,
            document=part_file,
            caption=f"✅ Final batch — Total tracks: {len(all_tracks)}"
        )

    await status_msg.edit("✅ Done! All artist track IDs fetched.") 
