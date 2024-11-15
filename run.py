import logging
import os
import asyncio

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers import router as user_router
from app.database.models import async_main


async def main():
    # Load environment variables
    load_dotenv()

    # Initialize bot and dispatcher
    storage = MemoryStorage()
    bot = Bot(token=os.getenv('TOKEN'))
    dp = Dispatcher(storage=storage)

    # Create database tables
    await async_main()

    # Include routers
    dp.include_router(user_router)

    # Start polling
    await dp.start_polling(bot, storage=storage)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
