from pyrogram import Client, filters
import os

COMBINED_FILE = "combined_track_ids.txt"

# 1. Auto combine track IDs when a .txt file is sent
@Client.on_message(filters.document & filters.private)
async def auto_combine_track_ids(client, message):
    if not message.document.file_name.endswith(".txt"):
        return  # Ignore other files

    file_path = await message.download()
    added_ids = 0

    try:
        with open(file_path, "r", encoding="utf-8") as incoming_file:
            incoming_ids = [line.strip() for line in incoming_file if line.strip()]

        # Create file if not exists
        if not os.path.exists(COMBINED_FILE):
            open(COMBINED_FILE, "w", encoding="utf-8").close()

        # Load existing track IDs
        with open(COMBINED_FILE, "r", encoding="utf-8") as combined_file:
            existing_ids = set(line.strip() for line in combined_file if line.strip())

        # Append only new
        new_ids = [track_id for track_id in incoming_ids if track_id not in existing_ids]
        with open(COMBINED_FILE, "a", encoding="utf-8") as combined_file:
            for track_id in new_ids:
                combined_file.write(track_id + "\n")
                added_ids += 1

        await message.reply(f"✅ `{added_ids}` new track IDs added.")
    except Exception as e:
        await message.reply(f"❌ Error:\n`{e}`")


# 2. /clear command to wipe the combined file
@Client.on_message(filters.command("clear") & filters.private)
async def clear_combined_file(client, message):
    if os.path.exists(COMBINED_FILE):
        open(COMBINED_FILE, "w", encoding="utf-8").close()
        await message.reply("🧹 Combined track list cleared.")
    else:
        await message.reply("⚠️ No file to clear.")


# 3. Optional: Send the combined file on demand
@Client.on_message(filters.command("getfile") & filters.private)
async def send_combined_file(client, message):
    if os.path.exists(COMBINED_FILE):
        await message.reply_document(COMBINED_FILE, caption="📄 Combined Track IDs")
    else:
        await message.reply("⚠️ No combined file found yet.")
