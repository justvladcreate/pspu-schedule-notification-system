from aiogram import types
from aiogram.filters.command import Command

from config import BotSetup
import logging

logger = logging.getLogger(__name__)

bot_config = BotSetup()
bot = bot_config.BOT
dp = bot_config.DP

def handle():
    logger.info("Настриваем проверку сообщений...")

    # Хэндлер на команду /start
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message) -> None:
        await message.answer("Привет! Я эхо-бот. Отправь мне любое сообщение, и я его повторю.")

    # Хэндлер на остальные текстовые сообщения
    @dp.message()
    async def echo_handler(message: types.Message) -> None:
        await message.answer(f"Я получил твое сообщение: {message.text}")