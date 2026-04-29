from config import BotConfig
import logging
from .handlers import keyboard_handlers, text_handlers

logger = logging.getLogger(__name__)

async def run():
    bot_config = BotConfig()
    dp = bot_config.DP
    bot = bot_config.BOT

    # Подключаем роутеры
    dp.include_router(keyboard_handlers.router)
    dp.include_router(text_handlers.router)

    # Удаляем вебхук и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Слушаем новые события...")
    await dp.start_polling(bot)