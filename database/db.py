import re
import logging
import base64
from struct import pack
import motor.motor_asyncio
from pyrogram.file_id import FileId
from info import MONGO_URI, MONGO_NAME
from pymongo.errors import DuplicateKeyError
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


# ---------------------- File ID Decode Helpers ---------------------- #

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref


# ---------------------- Spotify Track Extractor ---------------------- #



def extract_track_id(caption: str) -> str | None:
    if not caption:
        logger.info("No caption provided.")
        return None

    match = re.search(r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)", caption)
    if match:
        track_id = match.group(1)
        logger.info(f"Extracted track ID from URL: {track_id} in caption: {caption}///{match}")
        return track_id

    match = re.search(r"\b([a-zA-Z0-9]{22})\b", caption)
    if match:
        track_id = match.group(1)
        logger.info(f"Extracted track ID (22 chars) from caption: {track_id}/////{match}")
        return track_id

    logger.info(f"No track ID found in caption: {caption}//// {match}")
    return None
    
# ---------------------- Database Handler ---------------------- #

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_NAME]
        self.dump_col = self.db["dump"]
        self.media_col = self.db["media"]

    # Dump file_id ↔️ track_id mapping
    async def save_dump_file_id(self, track_id: str, file_id: str):
        await self.dump_col.update_one(
            {"track_id": track_id},
            {"$set": {"file_id": file_id}},
            upsert=True
        )

    async def get_dump_file_id(self, track_id: str):
        doc = await self.dump_col.find_one({"track_id": track_id})
        return doc["file_id"] if doc and "file_id" in doc else None

    # Save Media File
    async def save_file(self, bot, media, message):
        try:
            file_id, file_ref = unpack_new_file_id(media.file_id)
            file_name = re.sub(r"[_\-.+]", " ", str(media.file_name or "Unknown"))
            caption = message.caption.html if message.caption and message.caption.html else message.caption.text if message.caption else None

            track_id = extract_track_id(caption)

            file_data = {
                "_id": file_id,
                "file_ref": file_ref,
                "file_name": file_name,
                "file_size": getattr(media, "file_size", 0),
                "file_type": getattr(media, "file_type", None),
                "mime_type": getattr(media, "mime_type", None),
                "caption": media.caption.html if getattr(media, "caption", None) else None,
                "chat_id": str(message.chat.id),
                "msg_id": message.id,
                "track_id": track_id
            }

            await self.media_col.insert_one(file_data)
            logger.info(f"{file_name} saved to media DB")
            return True, 1

        except DuplicateKeyError:
            logger.warning(f"{file_name} already exists")
            return False, 0

        except Exception as e:
            logger.exception("Failed to save media")
            return False, 2


db = Database()
