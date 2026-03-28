import tempfile
import traceback
from pathlib import Path
from uuid import uuid4

import pdf417gen
from aiogram.types import FSInputFile
from PIL import Image

from core import logger
from x5_client import x5_mobile_client

BARCODE_IMAGE_SIZE = (472, 1024)


def get_card_number() -> str:
    data = x5_mobile_client.get_json("/common/api/cards/public/v1/card-list")
    return data["data"]["cards"][0]["card_number"]


def get_barcode_data() -> str:
    data = x5_mobile_client.get_json("/common/api/cards/public/v1/barcode")
    return data["data"]["barcode"]


def generate_pdf417(data: str):
    """Генерирует PDF417 штрихкод из строки data и сохраняет во временный файл."""
    encoded = pdf417gen.encode(data, columns=5, security_level=2)
    img = pdf417gen.render_image(encoded, scale=5)
    img = img.rotate(90, expand=True).convert("RGB")
    img.thumbnail(BARCODE_IMAGE_SIZE)

    canvas = Image.new("RGB", BARCODE_IMAGE_SIZE, "white")

    offset_x = (BARCODE_IMAGE_SIZE[0] - img.width) // 2
    offset_y = (BARCODE_IMAGE_SIZE[1] - img.height) // 2
    canvas.paste(img, (offset_x, offset_y))
    qr_path = Path(tempfile.gettempdir()) / f"x5m-barcode-{uuid4().hex}.png"
    canvas.save(qr_path)
    return qr_path


async def get_barcode_image() -> tuple[FSInputFile, Path]:
    card_number = get_card_number()
    logger.info(f"Card number: {card_number}")
    barcode_str = get_barcode_data()
    logger.info(f"Barcode content: {barcode_str}")
    qr_path = generate_pdf417(barcode_str)
    return FSInputFile(qr_path), qr_path


async def send_error(bot, chat_id: int, error: Exception) -> None:
    logger.error("Bot flow error", exc_info=(type(error), error, error.__traceback__))
    trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    await bot.send_message(
        chat_id,
        f"Error:\n<pre>{trace[-3500:]}</pre>",
        parse_mode="HTML",
    )
