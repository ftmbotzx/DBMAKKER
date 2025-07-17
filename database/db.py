import re
import logging
import motor.motor_asyncio
from pyrogram.file_id import FileId
from info import MONGO_URI, MONGO_NAME
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError

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
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_NAME]
        self.dump_col = self.db["dump"]
        self.media_col = self.db["media"]

    # ------------------ Dump file_id ↔️ track_id ------------------ #

    async def save_dump_file_id(self, track_id: str, file_id: str):
        await self.dump_col.update_one(
            {"track_id": track_id},
            {"$set": {"file_id": file_id}},
            upsert=True
        )

    async def get_dump_file_id(self, track_id: str):
        doc = await self.dump_col.find_one({"track_id": track_id})
        return doc["file_id"] if doc and "file_id" in doc else None

    # ------------------ Save Media to DB ------------------ #

    async def save_file(self, bot, media):
        try:
            file_id, file_ref = unpack_new_file_id(media.file_id)
            file_name = re.sub(r"[_\-.+]", " ", str(media.file_name or "Unknown"))
            file_data = {
                "_id": file_id,
                "file_ref": file_ref,
                "file_name": file_name,
                "file_size": getattr(media, "file_size", 0),
                "file_type": getattr(media, "file_type", None),
                "mime_type": getattr(media, "mime_type", None),
                "caption": media.caption.html if getattr(media, "caption", None) else None,
                "chat_id": str(media.chat.id),
                "msg_id": str(media.id)
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


# Initialize
db = Database()
