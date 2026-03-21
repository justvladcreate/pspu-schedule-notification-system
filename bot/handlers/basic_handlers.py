from aiogram import types, Router, F
from aiogram.filters.command import Command

import logging
logger = logging.getLogger(__name__)

router = Router()

logger.info("Настриваем проверку сообщений...")



# # Хэндлер на остальные текстовые сообщения
# @router.message(F.text)
# async def echo_handler(message: types.Message) -> None:
#     if message.text.lower() == "расскажи анекдот":
#         await message.answer(f"Меня не учили юмору!")