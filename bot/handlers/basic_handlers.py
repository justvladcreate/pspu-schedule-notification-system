from aiogram import types, Router, F
from aiogram.types import Message
import logging
from parser.process import process_schedule
from config import BotConfig

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == 'Запустить парсер')
async def trigger_parser(message: Message):
    if message.from_user.id not in BotConfig.ADMINS:
        return
    await message.answer("⏳ Запускаю парсер...")
    result = await process_schedule()
    if result:
        await message.answer("✅ Парсинг завершён!")
    else:
        await message.answer("❌ Ошибка при парсинге. Проверьте логи.")
