import os 
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass
from aiogram import Bot, Dispatcher


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


@dataclass
class BotSetup:
   
    load_env_file()
    config = load_config_from_yaml()

    TOKEN: str = config['testing_bot_token']
    # CHANNEL_CHAT_ID: int = -1003206831079
    # DATABASE_URL: str = "sqlite:///users.db"
    
    # Объект бота
    BOT = Bot(token=TOKEN)
    # Диспетчер
    DP = Dispatcher()
