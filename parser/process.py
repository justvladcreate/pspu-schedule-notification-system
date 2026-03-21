# [file name]: process.py
from .extractor import DataExtractor
from .preprocess import DataParser
from .postprocess import DataManager
from bot.middleware.messages import send_channel_post, send_user_notification
from pathlib import Path
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)


data_extractor = DataExtractor()
parser = DataParser()
manager = DataManager()


async def process_schedule():
    """Основной метод обработки расписания"""
    try:
        
        current_dir = Path(__file__).resolve().parent

        excel_path = Path(current_dir / "data\\pspu_schedule_latest.xlsx")
        old_excel_path = Path(current_dir / "data\\old_pspu_schedule_latest.xlsx")
        
        # Загрузка и обработка файлов
        if not _handle_files(excel_path, old_excel_path):
            logger.error("Не удалось обработать файлы")
            return False
        
        # Извлечение данных
        groups_info_old = data_extractor.extract(old_excel_path)
        groups_info_old = parser.parse(groups_info_old)
        
        groups_info = data_extractor.extract(excel_path)
        groups_info = parser.parse(groups_info)
        
        # Сохранение данных
        _save_data(groups_info, groups_info_old)
        
        # Сравнение изменений
        changes = manager.compare(groups_info_old, groups_info)
        
        # Отправка уведомлений
        if changes:
            await _send_notifications(changes)
        
        logger.info("Обработка расписания завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при обработке расписания: {e}")
        return False

def _handle_files(excel_path, old_excel_path):
    """Обработка файлов"""
    try:
        if old_excel_path.exists():
            if (excel_path.exists() and excel_path.is_file()):
                data_extractor.delete_old_file(excel_path)
            if not (excel_path.exists() and excel_path.is_file()):
                data_extractor.download_file(excel_path)
        else:
            data_extractor.delete_old_file(excel_path, max_time=0)
            if not (excel_path.exists() and excel_path.is_file()):
                data_extractor.download_file(excel_path)
        return True
                
    except PermissionError:
        logger.error("Не удалось удалить старый и скачать новый файлы, пропускаем.")
        if not (excel_path.exists() and excel_path.is_file()):
            data_extractor.download_file(excel_path)
        return True
    except Exception as e:
        logger.error(f"Ошибка при работе с файлами: {e}")
        return False

def _save_data(groups_info, groups_info_old):
    """Сохранение данных в JSON"""
    try:
        with open("data\\groups_info.json", "w", encoding="utf-8") as f:
            json.dump(groups_info, f, ensure_ascii=False, indent=4)
        with open("data\\groups_info_old.json", "w", encoding="utf-8") as f:
            json.dump(groups_info_old, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных: {e}")

def _send_notifications(changes):
    """Отправка уведомлений"""
    try:
        all_changes = {"general":[], "groups":[], "teachers":[]}
        messages = defaultdict(list)
        
        for changes_type, changes_list in changes.items():
            if changes_type == "general":
                all_changes["general"].extend(changes_list)
            elif changes_type == "groups":
                for group_name, changes in changes_list.items():
                    group_changes = []
                    group_changes.append(f"[{group_name}]")
                    group_changes.extend(changes)
                    group_changes.append("")
                    messages[group_name].extend(changes)
                    all_changes["groups"].extend(group_changes)
            else:
                for teachers, teachers_changes in changes_list.items():
                    all_changes["teachers"].append(f"[{teachers}]")
                    group_changes = []
                    for group_name, change in teachers_changes.items():
                        group_changes.append(f"• {group_name}")
                        group_changes.extend(change)
                    all_changes["teachers"].extend(group_changes)
                    all_changes["teachers"].append("")
                    
                    individual_teachers = [t.strip() for t in teachers.replace("\n", ",").split(",") if t.strip()]
                    for individual_teacher in individual_teachers:
                        messages[individual_teacher].extend(group_changes)
                        messages[individual_teacher].append("")
        
        # Отправка персональных уведомлений
        for title, changes in messages.items():
            message = f"[{title}]\n" + "\n".join(changes)
            message = message.rstrip("\n")
            # logger.info(message)
            send_user_notification(title, message)
        
        # Отправка общих уведомлений в канал
        if all_changes:
            final_message_parts = []
            
            if all_changes["general"]:
                final_message_parts.extend(all_changes["general"])
                final_message_parts.append("")
            
            if all_changes["groups"]:
                final_message_parts.extend(all_changes["groups"])
                final_message_parts.append("")
            
            if all_changes["teachers"]:
                final_message_parts.extend(all_changes["teachers"])
            
            while final_message_parts and final_message_parts[-1] == "":
                final_message_parts.pop()
            
            final_message = "\n".join(final_message_parts)
            
            # Отправляем только изменения преподавателей в канал
            send_channel_post("\n".join(all_changes["teachers"]))
            
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений: {e}")
