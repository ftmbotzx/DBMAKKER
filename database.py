import motor.motor_asyncio
from info import MONGO_URI, MONGO_NAME, MAINTENANCE_MODE
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_NAME]
        self.col = self.db["dump"]

    def new_user(self, id, name):
        return {"id": int(id), "name": name}

    # ----------- Dump cache methods -------------

    async def get_dump_msg_id(self, track_id: str):
        doc = await self.col.find_one({"track_id": track_id})
        if doc:
            return doc.get("dump_msg_id")
        return None

    async def save_dump_msg_id(self, track_id: str, dump_msg_id: int):
        await self.col.update_one(
            {"track_id": track_id},
            {"$set": {
                "dump_msg_id": dump_msg_id,
                "timestamp": datetime.utcnow()  # optional, for future cleanup
            }},
            upsert=True
        )

# create instance
db = Database()
