from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

from pyrogram.types import Message
from pyrogram.errors import FloodWait
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)



client_id = "e54b28b15f574338a709fdbde414b428"
client_secret = "7dead9452e6546fabdc9ad09ed00f172"

auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)





def extract_user_id(url):
    match = re.search(r"spotify\.com/user/([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None

@Client.on_message(filters.command("ur"))
async def user_tracks_split(client, message):
    if len(message.command) < 2:
        await message.reply("❗ Usage: `/ur <spotify_user_link>`")
        return

    user_url = message.command[1]
    user_id = extract_user_id(user_url)

    if not user_id:
        await message.reply("⚠️ Invalid Spotify user link!")
        return

    try:
        status = await message.reply(f"⏳ Fetching playlists for `{user_id}`...")

        playlists = sp.user_playlists(user_id)
        if not playlists['items']:
            await status.edit("⚠️ No public playlists found for this user.")
            return

        all_ids = []
        total_tracks = 0
        total_playlists = 0

        while playlists:
            for playlist in playlists['items']:
                total_playlists += 1
                pname = playlist['name']
                pid = playlist['id']

                await status.edit(
                    f"🔍 Processing playlist: **{pname}**\n"
                    f"✅ Playlists done: {total_playlists}\n"
                    f"🎵 Tracks so far: {total_tracks}"
                )

                tracks = sp.playlist_tracks(pid)

                while tracks:
                    for item in tracks['items']:
                        track = item['track']
                        if track:
                            tid = track['id']
                            all_ids.append(tid)
                            total_tracks += 1

                            # Optionally: update progress every 1000 tracks
                            if total_tracks % 200 == 0:
                                await status.edit(
                                    f"📦 Still fetching...\n"
                                    f"✅ Playlists done: {total_playlists}\n"
                                    f"🎵 Tracks so far: {total_tracks}"
                                )

                    if tracks['next']:
                        tracks = sp.next(tracks)
                    else:
                        tracks = None

            if playlists['next']:
                playlists = sp.next(playlists)
            else:
                playlists = None

        # Split into chunks of 5000
        chunk_size = 5000
        chunks = [all_ids[i:i + chunk_size] for i in range(0, len(all_ids), chunk_size)]

        part_number = 1
        for chunk in chunks:
            file_name = f"{user_id}_tracks_part{part_number}.txt"
            with open(file_name, "w", encoding="utf-8") as f:
                for tid in chunk:
                    f.write(f"{tid}\n")

            await client.send_document(
                chat_id=message.chat.id,
                document=file_name,
                caption=f"✅ `{user_id}` | Part {part_number} | {len(chunk)} track IDs"
            )
            part_number += 1

        await status.edit(
            f"🎉 **Done!** Total playlists: `{total_playlists}` | Total tracks: `{total_tracks}` | Files: `{len(chunks)}`"
        )

    except Exception as e:
        await status.edit(f"❌ Error: `{e}`")


@Client.on_message(filters.command("user"))
async def usernn_count(client, message):
    if len(message.command) < 2:
        await message.reply("❗ Usage: `/usercount <spotify_user_link>`")
        return

    user_url = message.command[1]
    user_id = extract_user_id(user_url)

    if not user_id:
        await message.reply("⚠️ Invalid Spotify user link!")
        return

    try:
        playlists = sp.user_playlists(user_id)
        if not playlists['items']:
            await message.reply("⚠️ No public playlists found for this user.")
            return

        total_playlists = 0
        total_tracks = 0

        while playlists:
            for playlist in playlists['items']:
                total_playlists += 1
                total_tracks += playlist['tracks']['total']
            if playlists['next']:
                playlists = sp.next(playlists)
            else:
                playlists = None

        await message.reply(
            f"👤 **User:** `{user_id}`\n"
            f"📚 **Total Playlists:** {total_playlists}\n"
            f"🎵 **Total Tracks in All Playlists:** {total_tracks}"
        )

    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")




@Client.on_message(filters.command("allartists"))
async def get_all_indian_artists(client, message):
    try:
        queries = [
            "top hindi songs", "top bollywood", "top punjabi hits", "latest gujarati songs",
            "indian classical", "indie india", "top tamil hits", "top telugu songs",
            "top marathi tracks", "indian rap", "indian pop", "arijit singh", "shreya ghoshal",
            "regional india", "indian devotional", "desi hip hop"
        ]

        artists_dict = {}

        for query in queries:
            results = sp.search(q=query, type='track', limit=50, market='IN')
            for item in results['tracks']['items']:
                for artist in item['artists']:
                    artists_dict[artist['name']] = f"https://open.spotify.com/artist/{artist['id']}"

        # Sorted artist list
        sorted_artists = sorted(artists_dict.items())
        total_count = len(sorted_artists)

        # Build final text
        text = f"🇮🇳 **All Indian Artist List (Auto Compiled)**\n🎧 **Total Unique Artists Found:** {total_count}\n\n"
        for idx, (name, url) in enumerate(sorted_artists, 1):
            text += f"{idx}. [{name}]({url})\n"

        # Save to .txt file (no markdown, just raw)
        plain_text = "\n".join([f"{idx}. {name} - {url}" for idx, (name, url) in enumerate(sorted_artists, 1)])
        with open("indian_artists_list.txt", "w", encoding="utf-8") as f:
            f.write(plain_text)

        await message.reply_document(
            "indian_artists_list.txt",
            caption=f"✅ Found `{total_count}` unique Indian artists via Spotify search."
        )

    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")


import asyncio
import re
from pyrogram import Client, filters
from spotipy import SpotifyException



def extract_artist_id(artist_url):
    match = re.search(r"artist/([a-zA-Z0-9]+)", artist_url)
    return match.group(1) if match else None

@Client.on_message(filters.command("artist") & filters.private & filters.reply)
async def artist_bulk_tracks(client, message):
    if not message.reply_to_message.document:
        await message.reply("❗ Please reply to a `.txt` file containing artist links.")
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
            # Fetch albums and singles
            album_ids = set()
            single_ids = set()

            results_albums = sp.artist_albums(artist_id, album_type='album', limit=50)
            album_ids.update([album['id'] for album in results_albums['items']])
            while results_albums['next']:
                results_albums = sp.next(results_albums)
                album_ids.update([album['id'] for album in results_albums['items']])

            results_singles = sp.artist_albums(artist_id, album_type='single', limit=50)
            single_ids.update([single['id'] for single in results_singles['items']])
            while results_singles['next']:
                results_singles = sp.next(results_singles)
                single_ids.update([single['id'] for single in results_singles['items']])

            all_album_ids = list(album_ids.union(single_ids))
            logger.info(f"Total releases: {len(all_album_ids)}")

            for idx, release_id in enumerate(all_album_ids, 1):
                try:
                    tracks = sp.album_tracks(release_id)
                    all_tracks.extend([track['id'] for track in tracks['items']])
                    await asyncio.sleep(0.2)

                    if idx % 50 == 0:
                        await asyncio.sleep(3)

                except SpotifyException as e:
                    if e.http_status == 429:
                        retry_after = int(e.headers.get("Retry-After", 5))
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        raise

        except Exception as e:
            await client.send_message(message.chat.id, f"⚠️ Error fetching `{artist_id}`: {e}")
            continue

        # Send in parts every 5000
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

    # Send remaining
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

