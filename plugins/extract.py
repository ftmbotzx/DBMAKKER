from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
from database.db import db 
from pyrogram.types import Message
from pyrogram.errors import FloodWait
import logging
import os
import re
import time
import json
import asyncio
from datetime import datetime
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__) 



client_secret = "3c7b577a92174fafb522039a52b2bc36"
client_id = "f4073094a91849bb9153c0b67b574806"

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


async def safe_spotify_call(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                logger.warning(f"🔁 429 Error. Retrying after {retry_after}s...")
                await asyncio.sleep(retry_after + 1)
            else:
                raise
               
PROGRESS_FILE = "progress.json"

import os
import time
import json
import re
import asyncio


@Client.on_message(filters.command("sa") & filters.private & filters.reply)
async def artist_bulk_tracks(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply("❗ Please reply to a `.txt` file containing artist links.")
        return

    args = message.text.strip().split()
    manual_skip = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    status_msg = await message.reply("📥 Downloading file...")

    file_path = await message.reply_to_message.download()
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    all_tracks = []
    request_counter = 0
    start_index = 0
    last_reset = time.time()

    if manual_skip is not None:
        start_index = manual_skip
        artist_counter = start_index
        await message.reply(f"⏩ Starting from artist #{start_index+1} (manual skip).")
    elif os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as pf:
                content = pf.read().strip()
                if not content:
                    raise ValueError("Progress file is empty.")
                progress = json.loads(content)
                start_index = progress.get("artist_index", 0)
                request_counter = progress.get("request_counter", 0)
                all_tracks = progress.get("all_tracks", [])
            artist_counter = start_index
            await message.reply(f"🔄 Resuming from artist #{start_index+1} with {request_counter} requests used.")
        except Exception as e:
            await message.reply(f"⚠️ Progress file corrupted or empty. Starting fresh.\n\nError: {e}")
            start_index = 0
            request_counter = 0
            all_tracks = []
            artist_counter = 0
    else:
        await message.reply("🚀 Starting fresh...")
        artist_counter = 0

    for idx in range(start_index, len(lines)):
        line = lines[idx].strip()
        match = re.search(r"spotify\.com/artist/([a-zA-Z0-9]+)", line)
        if not match:
            continue

        artist_id = match.group(1)
        artist_counter += 1

        await status_msg.edit(f"🎧 Processing Artist #{artist_counter}: `{artist_id}`")

        artist_tracks = []

        try:
            if request_counter >= 90:
                elapsed = time.time() - last_reset
                if elapsed < 60:
                    await asyncio.sleep(60 - elapsed)
                request_counter = 0
                last_reset = time.time()

            logger.info(f"🎤 Fetching albums for Artist {artist_counter}: {artist_id}")
            album_ids = set()

            results = await safe_spotify_call(sp.artist_albums, artist_id, album_type='album,single,appears_on,compilation', limit=50)
            request_counter += 1
            album_ids.update([album['id'] for album in results['items']])

            while results['next']:
                results = await safe_spotify_call(sp.next, results)
                request_counter += 1
                album_ids.update([album['id'] for album in results['items']])

            logger.info(f"📀 Total releases: {len(album_ids)}")

            for release_id in album_ids:
                try:
                    tracks = await safe_spotify_call(sp.album_tracks, release_id)
                    request_counter += 1
                    for track in tracks['items']:
                        track_id = track['id']
                        exists = await db.get_dump_file_id(track_id)
                        if exists:
                            continue
                        artist_tracks.append(track_id)

                    await asyncio.sleep(0.2)

                    if request_counter % 50 == 0:
                        await asyncio.sleep(3)

                except Exception as e:
                    if hasattr(e, 'http_status') and e.http_status == 429:
                        retry_after = int(e.headers.get("Retry-After", 5))
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        partial_filename = f"ratelimit_artist_{artist_id}_{timestamp}.txt"
                        with open(partial_filename, "w", encoding="utf-8") as pf:
                            pf.write("\n".join(artist_tracks))

                        await client.send_document(
                            chat_id=message.chat.id,
                            document=partial_filename,
                            caption=f"⚠️ Rate limited during artist `{artist_id}`.\nTracks collected: {len(artist_tracks)}\nResume with `/sa {idx}`"
                        )

                        with open(PROGRESS_FILE, "w", encoding="utf-8") as pf:
                            json.dump({
                                "artist_index": idx,
                                "request_counter": request_counter,
                                "all_tracks": all_tracks + artist_tracks
                            }, pf)
                        os.remove(file_path)
                        return
                    else:
                        raise

        except Exception as e:
            if hasattr(e, 'http_status') and e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                partial_filename = f"ratelimit_artist_{artist_id}_{timestamp}.txt"
                with open(partial_filename, "w", encoding="utf-8") as pf:
                    pf.write("\n".join(artist_tracks))

                await client.send_document(
                    chat_id=message.chat.id,
                    document=partial_filename,
                    caption=f"⛔ Rate limit hit!\nArtist: `{artist_id}` (#{artist_counter})\nResume with `/sa {idx}`"
                )

                with open(PROGRESS_FILE, "w", encoding="utf-8") as pf:
                    json.dump({
                        "artist_index": idx,
                        "request_counter": request_counter,
                        "all_tracks": all_tracks + artist_tracks
                    }, pf)
                os.remove(file_path)
                return
            else:
                logger.warning(f"⚠️ Error with artist {artist_id}: {e}")
                await client.send_message(message.chat.id, f"⚠️ Error fetching `{artist_id}`: {e}")
                continue

        if artist_tracks:
            artist_info = await safe_spotify_call(sp.artist, artist_id)
            artist_name = artist_info.get("name", artist_id)
            filename = f"artist_{artist_name}__{artist_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(artist_tracks))

            await client.send_document(
                chat_id=message.chat.id,
                document=filename,
                caption=f"✅ Artist #{artist_counter}: - {artist_name}__`{artist_id}` — {len(artist_tracks)} tracks"
            )

            all_tracks.extend(artist_tracks)
            await asyncio.sleep(1)

        # Save progress
        with open(PROGRESS_FILE, "w", encoding="utf-8") as pf:
            json.dump({
                "artist_index": idx + 1,
                "request_counter": request_counter,
                "all_tracks": all_tracks
            }, pf)

        if request_counter >= 10000:
            await message.reply(f"⛔ 10,000 request limit reached. Progress saved at artist #{idx+1}.")
            os.remove(file_path)
            return

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    await status_msg.edit("✅ Done! All artist track IDs fetched.")
    os.remove(file_path)

@Client.on_message(filters.command("checkall") & filters.private & filters.reply)
async def check_tracks_in_db(client, message):
    if not message.reply_to_message.document:
        await message.reply("❗ Please reply to a `.txt` file containing track IDs (one per line).")
        return

    status_msg = await message.reply("📥 Downloading file and starting processing...")

    file_path = await message.reply_to_message.download()
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_tracks = len(lines)
    new_tracks = []
    already_in_db = 0

    for idx, track_id in enumerate(lines, 1):
        try:
            exists = await db.get_dump_file_id(track_id)
            if not exists:
                new_tracks.append(track_id)
            else:
                already_in_db += 1

            if idx % 100 == 0 or idx == total_tracks:
                text = (
                    f"Processing tracks...\n"
                    f"Total tracks: {total_tracks}\n"
                    f"Checked: {idx}\n"
                    f"Already in DB: {already_in_db}\n"
                    f"New tracks to add: {len(new_tracks)}"
                )
                try:
                    await status_msg.edit(text)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                except Exception:
                    pass

        except FloodWait as e:
            await asyncio.sleep(e.x)
            continue
        except Exception as e:
            print(f"Error checking track {track_id}: {e}")
            continue

    batch_size = 5000
    batches = [new_tracks[i:i + batch_size] for i in range(0, len(new_tracks), batch_size)]

    for i, batch in enumerate(batches, 1):
        filename = f"new_tracks_part_{i}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(batch))

        await client.send_document(
            chat_id=message.chat.id,
            document=filename,
            caption=f"✅ New Tracks Batch {i}/{len(batches)} - {len(batch)} tracks"
        )
        await asyncio.sleep(3)

    await status_msg.edit(
        f"✅ Done!\n"
        f"Total tracks in file: {total_tracks}\n"
        f"Already in DB: {already_in_db}\n"
        f"New tracks files sent: {len(batches)}"
    )
