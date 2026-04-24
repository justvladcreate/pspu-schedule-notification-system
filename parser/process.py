from parser.extractor import DataExtractor
from google.auth.exceptions import RefreshError
from pathlib import Path
import logging
import json
import asyncio
import aiofiles.os
from parser.ai import ask_ai, user_prompt
from parser.finalize import transform_schedule

# from parser.process import handle_files

logger = logging.getLogger(__name__)

current_dir = Path(__file__).resolve().parent.parent

latest_files_path = current_dir / "data/latest"
old_files_path = current_dir / "data/old"

excel_file_name = "pspu_schedule.xlsx"
groups_info_extracted_and_cleaned_file_name = "groups_info_extracted_and_cleaned.json"
groups_info_after_ai_file_name = "groups_info_after_ai.json"
groups_info_parsed_file_name = "groups_info_parsed.json"

latest_excel_path = Path(latest_files_path / excel_file_name)
old_excel_path = Path(old_files_path / excel_file_name)

old_groups_info_extracted_and_cleaned_path = Path(old_files_path / groups_info_extracted_and_cleaned_file_name)
latest_groups_info_extracted_and_cleaned_path = Path(latest_files_path / groups_info_extracted_and_cleaned_file_name)

old_groups_info_after_ai_path = Path(old_files_path / groups_info_after_ai_file_name)
latest_groups_info_after_ai_path = Path(latest_files_path / groups_info_after_ai_file_name)

old_groups_info_parsed_path = Path(old_files_path / groups_info_parsed_file_name)
latest_groups_info_parsed_path = Path(latest_files_path / groups_info_parsed_file_name)

data_extractor = DataExtractor()

async def handle_excel_files(latest_excel, old_excel):
    """Обработка файлов"""
    try:
        if old_excel.exists():
            if latest_excel.exists() and latest_excel.is_file():
                data_extractor.delete_old_file(latest_excel)
            if not (latest_excel.exists() and latest_excel.is_file()):
                await data_extractor.download_file(latest_excel)
        else:
            if latest_excel.exists(): data_extractor.delete_old_file(latest_excel, max_time=0)
            if not (latest_excel.exists() and latest_excel.is_file()):
                await data_extractor.download_file(latest_excel)
        return True
    except PermissionError:
        logger.error("Не удалось удалить старый и скачать новый файлы - нет прав, пропускаем.")
        if not (latest_excel.exists() and latest_excel.is_file()):
            await data_extractor.download_file(latest_excel)
        return True
    except RefreshError as e:
        logger.error(f"Клиент credentials Oauth не найден или устаревший token: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при работе с файлами: {e}")
        return False

async def handle_json_files(data, latest_path, old_path):
    """Обработка файлов"""
    try:
        if old_path.exists():
            if latest_path.exists() and latest_path.is_file():
                await aiofiles.os.remove(latest_path)
            if not (latest_path.exists() and latest_path.is_file()):
                await save_data(data, latest_path)
        else:
            if latest_path.exists():
                await aiofiles.os.remove(latest_path)
            if not (latest_path.exists() and latest_path.is_file()):
                await save_data(data, latest_path)
        return True

    except PermissionError:
        logger.error("Не удалось удалить старый и скачать новый файлы - нет прав, пропускаем.")
        if not (latest_path.exists() and latest_path.is_file()):
            await data_extractor.download_file(latest_path)
        return True
    except RefreshError as e:
        logger.error(f"Клиент credentials Oauth не найден или устаревший token: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при работе с файлами: {e}")
        return False

async def save_data(data, path: str):
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


async def process_schedule():
    """Основной метод обработки расписания"""
    logger.info("Начата обработка расписания")
    # Загрузка из гугл таблиц
    if not await handle_excel_files(latest_excel_path, old_excel_path):
        logger.error("Не удалось обработать файлы")
        return False

    # Обработка полученной таблицы
    groups_info = await data_extractor.extract(latest_excel_path)
    groups_info_after_ai = {}
    for group, data in groups_info.items():
        prompt_text = user_prompt + str(data)
        group_info_after_ai = await ask_ai(prompt=prompt_text)
        groups_info_after_ai[group] = {"events": group_info_after_ai}   # создаём ключ и присваиваем значение

    # Промежуточное сохранение
    await handle_json_files(groups_info, latest_groups_info_extracted_and_cleaned_path, old_groups_info_extracted_and_cleaned_path)
    await handle_json_files(groups_info_after_ai, latest_groups_info_after_ai_path, old_groups_info_after_ai_path)

    # Сведение к рабочему виду
    groups_info = transform_schedule(groups_info_after_ai)
    await handle_json_files(groups_info, latest_groups_info_parsed_path, old_groups_info_parsed_path )
    return None



asyncio.run(process_schedule())