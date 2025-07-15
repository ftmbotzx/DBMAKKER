from pyrogram import Client, filters
import subprocess
import os


ffmpeg_path = "/usr/bin/ffmpeg"
download_path = "./downloads"

if not os.path.exists(download_path):
    os.makedirs(download_path)

app = Client

@app.on_message(filters.command("dl") & filters.private)
async def download_song(client, message):
    if len(message.command) < 2:
        await message.reply("❌ Send command as:\n/dl <spotify_link>")
        return

    url = message.command[1]
    status = await message.reply("⏳ Downloading, please wait...")

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
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        # Debug output
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

    except subprocess.CalledProcessError as e:
        # Ye pure spotdl ka stdout aur stderr capture karega
        error_msg = f"❌ SpotDL Error:\n\nSTDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}"
        if len(error_msg) > 4096:
            error_msg = error_msg[:4000] + "\n\n[...output truncated]"
        await status.edit(error_msg)
        return

    files = [f for f in os.listdir(download_path) if f.endswith(".mp3")]
    if not files:
        await status.edit("❌ Download failed, no file found.")
        return

    files.sort(key=lambda x: os.path.getmtime(os.path.join(download_path, x)), reverse=True)
    file_path = os.path.join(download_path, files[0])

    await client.send_audio(chat_id=message.chat.id, audio=file_path)
    os.remove(file_path)
    await status.edit("✅ Downloaded & sent successfully!")

