from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import REFRESH_BUTTON_TEXT

REFRESH_BARCODE_CALLBACK = "refresh_barcode"


async def refresh_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=REFRESH_BUTTON_TEXT, callback_data=REFRESH_BARCODE_CALLBACK)],
        ]
    )
