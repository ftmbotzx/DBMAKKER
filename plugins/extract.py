from pyrogram import Client, filters
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

client_id = "feef7905dd374fd58ba72e08c0d77e70"
client_secret = "60b4007a8b184727829670e2e0f911ca"
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

app = Client
# Helper function to extract artist ID from Spotify artist URL
def extract_artist_id(url):
    match = re.search(r"artist/([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None

@app.on_message(filters.command("artist_songs") & filters.private)
async def artist_songs(client, message):
    if len(message.command) < 2:
        await message.reply("Please send artist Spotify link.\nUsage: /artist_songs <artist_spotify_link>")
        return
    
    artist_url = message.command[1]
    artist_id = extract_artist_id(artist_url)
    
    if not artist_id:
        await message.reply("Invalid Spotify artist link. Please send a correct link.")
        return
    
    await message.reply("Fetching artist's songs data for India, please wait...")
    
    try:
        albums = []
        results = sp.artist_albums(artist_id, album_type='album,single', country='IN', limit=50)
        albums.extend(results['items'])
        
        # Pagination if more albums exist
        while results['next']:
            results = sp.next(results)
            albums.extend(results['items'])
        
        track_ids = set()
        for album in albums:
            album_id = album['id']
            tracks = sp.album_tracks(album_id)
            for track in tracks['items']:
                track_ids.add(track['id'])
        
        total_songs = len(track_ids)
        
        artist_info = sp.artist(artist_id)
        artist_name = artist_info['name']
        
        await message.reply(f"Artist: **{artist_name}**\nTotal Songs available in India: **{total_songs}**")
    
    except Exception as e:
        await message.reply(f"Error occurred: {e}")
