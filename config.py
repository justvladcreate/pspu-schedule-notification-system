import os 
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage


def load_env_file(path="private/.env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

def load_config_from_yaml(path="config.yaml"):
        
    with open(path, 'r') as file:
        raw_yaml = file.read()
        for key, value in os.environ.items():
            raw_yaml = raw_yaml.replace(f"${{{key}}}", value)
        config = yaml.safe_load(raw_yaml)
    return config


def setup_logging(logs_file: str = "info.log"):
    logs_file = Path(__file__).parent / "data" / logs_file
    logging.basicConfig(
        level=logging.INFO,
        encoding='utf-8',
        filename=logs_file,
        format='%(asctime)s\t| %(levelname)s\t| %(name)s\t| %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # очищаем файл логов, если его размер больше 10МБ
    if os.path.exists(logs_file) and os.path.getsize(logs_file) > 1024*10:
        with open(logs_file, 'w'):
            pass


setup_logging()

class BotConfig:
    load_env_file()
    config = load_config_from_yaml()
    admins_str = str(config.get('admin_ids', ''))
    ADMINS = []
    if admins_str:
        ADMINS = [int(x.strip()) for x in admins_str.split(',')]
    TOKEN: str = config['testing_bot_token']
    # CHANNEL_CHAT_ID: int = -1003206831079 #main channel
    CHANNEL_CHAT_ID: int = -1003862286446  # testing channel
    DATABASE_URL: str = "sqlite:///users.db"

    def __init__(self):
        # Объект бота
        self.BOT = Bot(token=self.TOKEN)
        # Диспетчер с FSM storage
        self.DP = Dispatcher(storage=MemoryStorage())

    async def send_message_to_user(self, user_id: int, text: str) -> None:
        try:
            await self.BOT.send_message(chat_id=user_id, text=text)
        except Exception as e:
            print(f"Ошибка при отправке: {e}")
