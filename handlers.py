import asyncio

from aiogram import F, Router, types
from aiogram.filters import CommandStart

import keyboards as kb
from config import ADMIN_ID, START_MESSAGE_TEXT
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

        loading_msg = await callback.message.answer('Загрузка...')

        photo, barcode_path = await get_barcode_image()
        try:
            await loading_msg.delete()
            barcode_message = await callback.message.answer_photo(
                photo=photo,
            )
        finally:
            await asyncio.to_thread(barcode_path.unlink, missing_ok=True)

        await asyncio.sleep(60 * 30)
        await barcode_message.delete()
    except Exception as error:
        await send_error(callback.bot, chat_id, error)
