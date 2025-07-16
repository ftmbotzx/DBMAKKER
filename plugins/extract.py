from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

client_id = "e54b28b15f574338a709fdbde414b428"
client_secret = "7dead9452e6546fabdc9ad09ed00f172"

auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

def extract_user_id(url):
    match = re.search(r"spotify\.com/user/([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None

@Client.on_message(filters.command("userpl"))
async def user_playlists(client, message):
    if len(message.command) < 2:
        await message.reply("❗ Usage: `/userpl <spotify_user_link>`")
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

        text = f"Public playlists by `{user_id}`:\n\n"
        total_count = 0

        while playlists:
            for playlist in playlists['items']:
                name = playlist['name']
                url = playlist['external_urls']['spotify']
                text += f"{url}\n"
                total_count += 1
            if playlists['next']:
                playlists = sp.next(playlists)
            else:
                playlists = None

        text += f"\nTotal Public Playlists: {total_count}"

        # Save to file
        file_name = f"{user_id}_playlists.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(text)

        # Send file
        await message.reply_document(
            file_name,
            caption=f"✅ Found `{total_count}` public playlists for `{user_id}`"
        )

    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")
