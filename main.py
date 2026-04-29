"""
Основной файл

Работает всегда, запускает скрипт парсера раз в 15 минут
Запускает/останавливает бота
"""

import logging
import asyncio
import bot.start_bot
from config import BotConfig
from parser.process import process_schedule

import aiogram

bot_config = BotConfig()

logger = logging.getLogger(__name__)

logger.info("Новый запуск основного скрипта.")
print("Используйте Ctrl+C чтобы остановить скрипт...")

CHECK_CHANGES_TIMER: int = 60*60

async def timer():
    try:
        while True:
            await process_schedule()
            await asyncio.sleep(CHECK_CHANGES_TIMER)
            logger.info("Запуск парсера...")
    except asyncio.CancelledError:
        logger.info("Таймер парсера остановлен.")


async def main():
    # Запускаем таймер парсера как фоновую задачу
    timer_task = asyncio.create_task(timer())
    try:
        # Запускаем бота (блокирует до остановки)
        await bot.start_bot.run()
    finally:
        # После остановки бота отменяем таймер
        timer_task.cancel()
        try:
            await timer_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка основного скрипта пользователем.")
        print("Остановка скрипта.")
