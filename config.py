import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_NAME = os.getenv("BOT_NAME", "STORE BOT")
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/soporte")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/canal")
BANNER_PATH = os.getenv("BANNER_PATH", "assets/logo.png")
TASKS_URL = "https://rewafree.web.app"

ADMIN_IDS = set()
for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(","):
    if x.isdigit():
        ADMIN_IDS.add(int(x))
