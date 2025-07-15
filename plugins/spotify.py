from pyrogram import Client, filters
import subprocess
import os



# ffmpeg ka path agar custom hai to yahan set karein, nahi to None ya default ffmpeg
ffmpeg_path = "/usr/bin/ffmpeg"

# Download folder jahan files save hongi
download_path = "./downloads"

if not os.path.exists(download_path):
    os.makedirs(download_path)

app = Client

@app.on_message(filters.command("dl") & filters.private)
async def download_song(client, message):
    if len(message.command) < 2:
        await message.reply("Please send the command as:\n/download <youtube_track_url>")
        return

    url = message.command[1]
    await message.reply("Downloading your track, please wait...")

    # Construct spotdl command
    cmd = [
        "spotdl",
        "download",
        url,
        "--output", download_path,
        "--format", "mp3",
        "--bitrate", "320k",
        "--ffmpeg", ffmpeg_path
    ]

    try:
        # Run the download command synchronously (blocking)
        subprocess.run(cmd, check=True)

        # Find the downloaded file in the folder (spotdl saves by title.mp3)
        # So list the folder files and find latest mp3
        files = [f for f in os.listdir(download_path) if f.endswith(".mp3")]
        if not files:
            await message.reply("Download failed or no file found.")
            return

        # Assuming latest file is the downloaded one
        files.sort(key=lambda x: os.path.getmtime(os.path.join(download_path, x)), reverse=True)
        file_path = os.path.join(download_path, files[0])

        # Send audio file to user
        await client.send_audio(chat_id=message.chat.id, audio=file_path)
        # Optional: Delete file after sending
        os.remove(file_path)

    except subprocess.CalledProcessError as e:
        await message.reply(f"Error downloading track:\n{e}")

