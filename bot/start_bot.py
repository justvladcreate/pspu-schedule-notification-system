from config import BotSetup
import logging
from .echo_handler import handle

logger = logging.getLogger(__name__)

bot_config = BotSetup()
bot = bot_config.BOT
dp = bot_config.DP
handle()
# CHANNEL_CHAT_ID: int = -1003206831079
# DATABASE_URL: str = "sqlite:///users.db"


# Запуск процесса поллинга новых апдейтов
async def run():
    # Удаляем вебхук и пропускаем накопившиеся входящие сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Слушаем новые события...")
    await dp.start_polling(bot)
