from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

from pyrogram.types import Message


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


def extract_track_id_from_url(text):
    match = re.search(r"track/([a-zA-Z0-9]+)", text)
    return match.group(1) if match else None

async def search_track_id_from_text(query):
    results = sp.search(q=query, limit=1, type='track')
    items = results.get("tracks", {}).get("items", [])
    if items:
        return items[0]["id"], items[0]["duration_ms"]
    return None, None

def extract_track_id_from_caption(caption):
    match = re.search(r"track/([a-zA-Z0-9]+)", caption)
    if match:
        return match.group(1)
    return None

@Client.on_message(filters.command("fix") & filters.reply)
async def fix_audio_duration(client, message):
    reply = message.reply_to_message
    if not reply or not reply.audio:
        await message.reply("❗ Please reply to a Spotify song audio.")
        return

    caption = reply.caption or ""
    track_id = extract_track_id_from_url(caption)
    if not track_id:
        await message.reply("⚠️ Couldn't find Spotify track ID in caption.")
        return

    try:
        track = sp.track(track_id)
        duration_ms = track["duration_ms"]
        duration_sec = int(duration_ms / 1000)

        await message.reply_audio(
            audio=reply.audio.file_id,
            duration=duration_sec,
            caption=f"✅ Fixed duration from Spotify\n🎵 {track['name']} - {track['artists'][0]['name']}\n🔗 https://open.spotify.com/track/{track_id}"
        )

    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")
