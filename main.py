"""
Основной файл

Работает всегда, запускает скрипт парсера раз в 15 минут
Запускает/останавливает бота
"""

import logging
import asyncio
from bot.start_bot import run
from config import BotConfig
from parser.process import process_schedule


bot_config = BotConfig()

logger = logging.getLogger(__name__)

logger.info("Новый запуск основного скрипта.")
print("Используйте Ctrl+C чтобы остановить скрипт...")

CHECK_CHANGES_TIMER: int = 900


async def timer():
    timer_running = True
    
    while timer_running:
        await asyncio.sleep(CHECK_CHANGES_TIMER) 
        
        logger.info("Запуск парсера...")
        
        await process_schedule()
    

async def main():
    asyncio.create_task(timer())
    await run()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка основного скрипта пользователем.")
        print("Остановка скрипта.")
