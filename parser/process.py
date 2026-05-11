from google.auth.exceptions import RefreshError
from pathlib import Path
import logging
import json
import asyncio
import aiofiles.os
from parser.ai import ask_ai, user_prompt
from parser.extractor import DataExtractor, delete_old_file
from parser.finalize import transform_schedule
from parser.postprocess import compare_snapshots
from bot.middleware.database import SessionLocal, ChangeDetails
from bot.middleware.notifier import send_notifications

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
                delete_old_file(latest_excel, old_excel)
            if not (latest_excel.exists() and latest_excel.is_file()):
                await data_extractor.download_file(latest_excel)
        else:
            if latest_excel.exists(): delete_old_file(latest_excel, old_excel, max_time=0)
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

async def handle_json_files(data, latest_path: Path, old_path: Path):
    """
    Сохраняет свежий JSON-файл по пути latest_path,
    а предыдущую версию переносит в old_path (с заменой).
    """
    try:
        if latest_path.exists():
            if old_path.exists():
                await aiofiles.os.remove(old_path)
            await aiofiles.os.rename(latest_path, old_path)
        await save_data(data, str(latest_path))
        return True
    except PermissionError:
        logger.error("Не удалось удалить старый и скачать новый файлы - нет прав, пропускаем.")
        if not (latest_path.exists() and latest_path.is_file()):
            await save_data(data, str(latest_path))
        return True
    except RefreshError as e:
        logger.error(f"Клиент credentials Oauth не найден или устаревший token: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при работе с файлами: {e}")
        return False

async def save_data(data, path: str):
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=4))


async def process_schedule(use_chunks: bool = False, chunk_size: int = 12):
    """Основной метод обработки расписания с разбивкой на чанки"""
    logger.info("Начата обработка расписания")
    # Загрузка из гугл таблиц
    if not await handle_excel_files(latest_excel_path, old_excel_path):
        logger.error("Не удалось обработать файлы")
        return False

    # Обработка полученной таблицы
    groups_info = await data_extractor.extract(latest_excel_path)
    groups_info_after_ai = {}

    for group, group_data in groups_info.items():
        events_list = group_data.get("events", [])   # список строк
        if not events_list:
            groups_info_after_ai[group] = {"events": []}
            continue

        if not use_chunks: chunk_size = len(events_list)

        all_events = []
        # Разбиваем список на чанки
        for i in range(0, len(events_list), chunk_size):
            chunk = events_list[i:i+chunk_size]
            prompt_text = user_prompt.format(data=str(chunk))
            try:
                chunk_result = await ask_ai(prompt=prompt_text)
                # chunk_result - список строк, каждая = одно событие
                if isinstance(chunk_result, list):
                    all_events.extend(chunk_result)
                else:
                    # если вдруг вернулась строка, разбиваем по \n
                    all_events.extend(chunk_result.split("\n"))
            except Exception as e:
                logger.error(f"Ошибка AI для группы {group}, чанк {i//chunk_size}: {e}")
                # При ошибке можно пропустить чанк или прервать обработку группы
                # Пропускаем, чтобы не потерять уже обработанное
                continue
            # Небольшая задержка между чанками, чтобы не перегружать API
            await asyncio.sleep(0.5)

        groups_info_after_ai[group] = {"events": all_events}
        # break  # раскомментируйте, если нужно тестировать на одной группе

    # Промежуточное сохранение
    await handle_json_files(groups_info, latest_groups_info_extracted_and_cleaned_path, old_groups_info_extracted_and_cleaned_path)
    await handle_json_files(groups_info_after_ai, latest_groups_info_after_ai_path, old_groups_info_after_ai_path)

    #отладка
    # with open(latest_groups_info_after_ai_path, 'r') as file:
    #     groups_info_after_ai = json.load(file)

    # Сведение к рабочему виду
    groups_info = await transform_schedule(groups_info_after_ai)
    await handle_json_files(groups_info, latest_groups_info_parsed_path, old_groups_info_parsed_path )

    # Сравниваем с предыдущим снимком
    changes = compare_snapshots(
        str(latest_groups_info_parsed_path),
        str(old_groups_info_parsed_path)
    )

    if not changes:
        return None

    # Сохраняем изменения в БД с проверкой дубликатов
    session = SessionLocal()
    try:
        for change in changes:
            if change["change_type"] == "changed":
                for field in change["changes"]:
                    # Проверяем, нет ли уже такой записи
                    exists = session.query(ChangeDetails).filter_by(
                        change_type="changed",
                        event_id=change["event_id"],
                        field_name=field["field"],
                        old_value=field["old_value"],
                        new_value=field["new_value"]
                    ).first()
                    if not exists:
                        detail = ChangeDetails(
                            change_type="changed",
                            event_id=change["event_id"],
                            group_name=change["group"],
                            weekday=change["weekday"],
                            pair_number=change["pair_number"],
                            time=change.get("time", ""),
                            field_name=field["field"],
                            old_value=field["old_value"],
                            new_value=field["new_value"]
                        )
                        session.add(detail)
            else:
                # added или removed – дубликат ищем по event_id, типу, new_value/old_value
                if change["change_type"] == "added":
                    new_val = json.dumps(change["data"], ensure_ascii=False)
                    exists = session.query(ChangeDetails).filter_by(
                        change_type="added",
                        event_id=change["event_id"],
                        new_value=new_val
                    ).first()
                    if not exists:
                        log = ChangeDetails(
                            change_type="added",
                            event_id=change["event_id"],
                            group_name=change["group"],
                            weekday=change["weekday"],
                            pair_number=change["pair_number"],
                            time=change.get("time", ""),
                            new_value=new_val
                        )
                        session.add(log)
                elif change["change_type"] == "removed":
                    old_val = json.dumps(change["data"], ensure_ascii=False)
                    exists = session.query(ChangeDetails).filter_by(
                        change_type="removed",
                        event_id=change["event_id"],
                        old_value=old_val
                    ).first()
                    if not exists:
                        log = ChangeDetails(
                            change_type="removed",
                            event_id=change["event_id"],
                            group_name=change["group"],
                            weekday=change["weekday"],
                            pair_number=change["pair_number"],
                            time=change.get("time", ""),
                            old_value=old_val
                        )
                        session.add(log)

        session.commit()
        print("\n=== Содержимое change_details после сохранения ===")
        for row in session.query(ChangeDetails).order_by(ChangeDetails.id).all():
            print(f"id={row.id} | type={row.change_type} | event={row.event_id} | "
                  f"group={row.group_name} | {row.weekday} {row.time} | "
                  f"field={row.field_name} | old={row.old_value} | new={row.new_value}")
        print("===================================================\n")

        logger.info(f"Сохранено {len(changes)} изменений в change_log (дубликаты пропущены).")
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при сохранении изменений в БД: {e}")
    finally:
        session.close()

    # Отправка уведомлений
    await send_notifications(changes)

    return changes



# asyncio.run(process_schedule())