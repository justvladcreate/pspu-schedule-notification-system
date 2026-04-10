from aiogram import types, Router, F
from aiogram.types import Message
import logging
import json
from pathlib import Path
from parser.process import process_schedule, DATA_DIR
from parser.postprocess import DataManager
from parser.preprocess import DataParser
from bot.middleware.messages import send_channel_post, send_user_notification
from collections import defaultdict
from config import BotConfig

logger = logging.getLogger(__name__)

router = Router()

manager = DataManager()
parser = DataParser()


@router.message(F.text == 'Запустить парсер')
async def trigger_parser(message: Message):
    if message.from_user.id not in BotConfig.ADMINS:
        return
    await message.answer("⏳ Запускаю парсер...")
    result = await process_schedule()
    if result:
        await message.answer("✅ Парсинг завершён!")
    else:
        await message.answer("❌ Ошибка при парсинге. Проверьте логи.")


@router.message(F.text == 'Тест уведомлений')
async def test_notifications(message: Message):
    """
    Сравнивает groups_info.json и groups_info_old.json
    и отправляет уведомления по найденным изменениям.
    """
    if message.from_user.id not in BotConfig.ADMINS:
        return

    new_path = DATA_DIR / "groups_info.json"
    old_path = DATA_DIR / "groups_info_old.json"

    if not new_path.exists() or not old_path.exists():
        await message.answer(
            "❌ Нужны оба файла:\n"
            "• data/groups_info.json (новое)\n"
            "• data/groups_info_old.json (старое)\n\n"
            "Сначала запусти парсер, потом скопируй JSON и отредактируй."
        )
        return

    await message.answer("⏳ Сравниваю JSON файлы...")

    try:
        with open(old_path, "r", encoding="utf-8") as f:
            groups_info_old = json.load(f)
        with open(new_path, "r", encoding="utf-8") as f:
            groups_info = json.load(f)

        changes = manager.compare(groups_info_old, groups_info)

        if not changes:
            await message.answer("✅ Изменений не найдено.")
            return

        # Формируем сообщения
        all_changes = {"general": [], "groups": [], "teachers": []}
        messages = defaultdict(list)

        for changes_type, changes_list in changes.items():
            if changes_type == "general":
                all_changes["general"].extend(changes_list)
            elif changes_type == "groups":
                for group_name, group_changes in changes_list.items():
                    formatted = [f"[{group_name}]"]
                    formatted.extend(group_changes)
                    formatted.append("")
                    messages[group_name].extend(group_changes)
                    all_changes["groups"].extend(formatted)
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
                    for t in individual_teachers:
                        messages[t].extend(group_changes)
                        messages[t].append("")

        # Отправляем персональные уведомления
        sent_count = 0
        for title, change_list in messages.items():
            msg = f"[{title}]\n" + "\n".join(change_list).rstrip("\n")
            count = await send_user_notification(title, msg)
            sent_count += count

        # Показываем админу что нашлось
        summary_parts = []
        for section in ["general", "groups", "teachers"]:
            if all_changes[section]:
                summary_parts.extend(all_changes[section])

        summary = "\n".join(summary_parts).strip()
        if summary:
            from bot.middleware.messages import split_message
            for part in split_message(f"📊 Найденные изменения:\n\n{summary}"):
                await message.answer(part, parse_mode='HTML', disable_web_page_preview=True)

        await message.answer(f"📨 Отправлено уведомлений: {sent_count}")

    except Exception as e:
        logger.error(f"Ошибка тестирования уведомлений: {e}")
        await message.answer(f"❌ Ошибка: {e}")
