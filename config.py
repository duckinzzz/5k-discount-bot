import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
ENV = os.getenv("ENV", "prod").lower()
X5M_BEARER_TOKEN = os.getenv("X5M_BEARER_TOKEN")
X5M_API_BASE = os.getenv("X5M_API_BASE", "https://x5m.x5.ru")

HTTP_TIMEOUT_SECONDS = 15.0
START_MESSAGE_TEXT = "Нажмите кнопку для получения штрих-кода"
BARCODE_CAPTION = "Ваш штрих-код"
REFRESH_BUTTON_TEXT = "Обновить"

if not BOT_TOKEN or BOT_TOKEN == "NO_TOKEN":
    raise ValueError("BOT_TOKEN not found")

if not ADMIN_ID_RAW:
    raise ValueError("ADMIN_ID not found")

if ENV not in {"dev", "prod"}:
    raise ValueError("ENV must be 'dev' or 'prod'")

ADMIN_ID = int(ADMIN_ID_RAW)

_required_values = {
    "X5M_BEARER_TOKEN": X5M_BEARER_TOKEN,
}

_missing_values = [name for name, value in _required_values.items() if not value]
if ENV == "prod" and _missing_values:
    raise ValueError(f"Missing required .env values: {', '.join(_missing_values)}")
