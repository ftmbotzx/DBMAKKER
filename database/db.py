import re
import logging
import motor.motor_asyncio
from pyrogram.file_id import FileId
from info import MONGO_URI, MONGO_NAME

unpack_new_file_id = FileId

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
        except motor.motor_asyncio.AsyncIOMotorCollection.DuplicateKeyError:
            logger.warning(f"{file_name} already exists")
            return False, 0
        except Exception as e:
            logger.exception("Failed to save media")
            return False, 2

# Initialize
db = Database()
