import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand
from database import create_table
from handlers import register_handlers


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="стартуем"),
        BotCommand(command="/new_chart", description="график рисуем"),
        BotCommand(command="/goida", description="гойдим"),
    ]
    await bot.set_my_commands(commands)


async def main():
    logging.basicConfig(level=logging.INFO)

    with open("TOKEN.txt", "r") as f:
        token = f.read().strip()

    bot = Bot(token=token)
    dp = Dispatcher(bot, storage=MemoryStorage())

    register_handlers(dp)
    create_table()

    await set_commands(bot)
    await dp.skip_updates()
    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
