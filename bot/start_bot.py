from config import BotConfig
import logging
from .handlers import basic_handlers, keyboard_handlers

logger = logging.getLogger(__name__)

bot = BotConfig().BOT
dp = BotConfig().DP
# CHANNEL_CHAT_ID: int = -1003206831079
# DATABASE_URL: str = "sqlite:///users.db"
    
# Запуск процесса поллинга новых апдейтов
async def run():

    dp.include_router(basic_handlers.router)
    dp.include_router(keyboard_handlers.router)
    # Удаляем вебхук и пропускаем накопившиеся входящие сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Слушаем новые события...")
    await dp.start_polling(bot)
