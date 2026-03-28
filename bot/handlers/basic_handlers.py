from aiogram import types, Router, F
from aiogram.filters.command import Command
from aiogram.types import Message
import logging
from parser.process import process_schedule

logger = logging.getLogger(__name__)

router = Router()

logger.info("Настриваем проверку сообщений...")


@router.message(F.text == 'Запустить парсер')
async def get_inline_btn_link(message: Message):
    await process_schedule()
# # Хэндлер на остальные текстовые сообщения
# @router.message(F.text)
# async def echo_handler(message: types.Message) -> None:
#     if message.text.lower() == "расскажи анекдот":
#         await message.answer(f"Меня не учили юмору!")