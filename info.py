import os

SESSION = "my_bot"
API_ID = int(os.getenv("API_ID", "801239"))
API_HASH = os.getenv("API_HASH", "171e6f1c5140fbe827b6b08")
BOT_TOKEN = os.getenv("BOT_TOKEN", "653862OrA3AJn8t-YIKy_N_3Z6BsNc")
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1002379643238"))
DUMP_CHANNEL = int(os.getenv("DUMP_CHANNEL", "-1002379643238"))
PORT = int(os.getenv("PORT", "8080"))
