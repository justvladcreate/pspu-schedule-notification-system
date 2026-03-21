"""
Основной файл

Работает всегда, запускает скрипт парсера раз в 15 минут
Запускает/останавливает бота
"""

import logging
import asyncio
from config import setup_logging
from bot import start_bot

logger = logging.getLogger(__name__)
setup_logging()

logger.info("Новый запуск основного скрипта.")

if __name__ == "__main__":
    try:
        asyncio.run(start_bot.run())
    except KeyboardInterrupt:
        logger.info("Остановка основного скрипта пользователем.")