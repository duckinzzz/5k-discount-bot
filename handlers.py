import asyncio

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart

import keyboards as kb
from config import ADMIN_ID, BARCODE_CAPTION, START_MESSAGE_TEXT
from keyboards import REFRESH_BARCODE_CALLBACK
from utils import get_barcode_image, send_error

start_router = Router(name="start_router")
start_router.message.filter(F.from_user.id == ADMIN_ID)
start_router.callback_query.filter(F.from_user.id == ADMIN_ID)


@start_router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    try:
        await message.answer(
            START_MESSAGE_TEXT,
            reply_markup=await kb.refresh_kb(),
        )
    except Exception as error:
        await send_error(message.bot, message.chat.id, error)


@start_router.callback_query(F.data == REFRESH_BARCODE_CALLBACK)
async def refresh_barcode(callback: types.CallbackQuery) -> None:
    chat_id = callback.message.chat.id if callback.message else callback.from_user.id

    try:
        await callback.answer()

        if not callback.message:
            return

        try:
            await callback.message.delete()
        except TelegramBadRequest as error:
            if "message to delete not found" not in str(error).lower():
                raise

        photo, barcode_path = await get_barcode_image()
        try:
            await callback.message.answer_photo(
                photo=photo,
                caption=BARCODE_CAPTION,
                reply_markup=await kb.refresh_kb(),
            )
        finally:
            await asyncio.to_thread(barcode_path.unlink, missing_ok=True)
    except Exception as error:
        await send_error(callback.bot, chat_id, error)
