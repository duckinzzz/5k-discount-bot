import asyncio

from core import bot, dp, logger
from handlers import start_router


async def announce_start():
    logger.info("Bot started")


async def main():
    dp.include_router(start_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await announce_start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
