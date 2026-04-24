# [file name]: notifications.py
from .database import SessionLocal, User
from collections import defaultdict
from config import BotConfig

bot = BotConfig().BOT

async def send_user_notification(key: str, message_text: str) -> int:
    """
    Асинхронно отправляет уведомление всем пользователям, чье ФИО содержится в ключе.
    Возвращает количество успешно отправленных сообщений.
    """
    session = SessionLocal()
    success_count = 0
    
    # Обрабатываем ключ (могут быть несколько преподавателей через запятую)
    parts = key.strip().split(',')
    key = parts[-1].strip()  # Берем последнего преподавателя как ключ
    
    try:
        # Получаем всех пользователей из БД
        all_users = session.query(User).all()
        
        # Ищем пользователей, чей ключ совпадает
        for user in all_users:
            if user.key == key:
                try:
                    await bot.send_message(
                        user.telegram_id,
                        message_text,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    success_count += 1
                except Exception as e:
                    print(f"Ошибка отправки пользователю {user.telegram_id}: {e}")
                
        return success_count
    finally:
        session.close()

async def broadcast_message(message_text: str) -> dict:
    """
    Асинхронная рассылка сообщения всем пользователям.
    Возвращает статистику рассылки.
    """
    session = SessionLocal()
    stats = {"total": 0, "success": 0, "failed": 0}
    
    try:
        users = session.query(User).all()
        stats["total"] = len(users)
        
        for user in users:
            try:
                await bot.send_message(
                    user.telegram_id,
                    message_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                stats["success"] += 1
            except Exception as e:
                print(f"Ошибка отправки пользователю {user.telegram_id}: {e}")
                stats["failed"] += 1
                
        return stats
    finally:
        session.close()

async def send_channel_post(text: str) -> None:
    await bot.send_message(
        chat_id=BotConfig.CHANNEL_CHAT_ID,
        text=text,
        parse_mode='HTML',
        disable_web_page_preview=True,
        disable_notification=True
    )

async def _send_notifications(changes):
    """Отправка уведомлений"""
    try:
        all_changes = {"general":[], "groups":[], "teachers":[]}
        messages = defaultdict(list)

        for changes_type, changes_list in changes.items():
            if changes_type == "general":
                all_changes["general"].extend(changes_list)
            elif changes_type == "groups":
                for group_name, changes in changes_list.items():
                    group_changes = [f"[{group_name}]"]
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
            await send_user_notification(title, message)

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
            await send_channel_post("\n".join(all_changes["teachers"]))

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений: {e}")
