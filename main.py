"""
Основной файл

Работает всегда, запускает скрипт парсера раз в 15 минут
Запускает/останавливает бота
"""

import logging
import asyncio
from config import BotConfig
from parser.process import process_schedule

import aiogram

bot_config = BotConfig()

logger = logging.getLogger(__name__)

logger.info("Новый запуск основного скрипта.")
print("Используйте Ctrl+C чтобы остановить скрипт...")

CHECK_CHANGES_TIMER: int = 60  # секунды (60 = 1 минута, 900 = 15 минут)

async def timer():
    timer_running = True

    while timer_running:
        await asyncio.sleep(CHECK_CHANGES_TIMER)

        logger.info("Запуск парсера...")

        await process_schedule()


async def main():
    from bot.start_bot import bot, dp
    from bot.handlers import basic_handlers, keyboard_handlers

    dp.include_router(basic_handlers.router)
    dp.include_router(keyboard_handlers.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Слушаем новые события...")

    # Запускаем таймер и polling параллельно
    await asyncio.gather(
        dp.start_polling(bot),
        timer()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка основного скрипта пользователем.")
        print("Остановка скрипта.")
