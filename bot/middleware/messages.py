# [file name]: messages.py
from .database import SessionLocal, Subscription
from config import BotConfig

bot = BotConfig().BOT

MAX_MESSAGE_LENGTH = 4096


def split_message(text, max_length=MAX_MESSAGE_LENGTH):
    """Разбивает длинное сообщение на части по строкам"""
    if len(text) <= max_length:
        return [text]

    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_length:
            if current:
                parts.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line

    if current:
        parts.append(current)

    return parts


async def send_user_notification(key: str, message_text: str) -> int:
    """
    Отправляет уведомление пользователям, подписанным на данный ключ.
    Ключ может быть группой или ФИО преподавателя.
    """
    session = SessionLocal()
    success_count = 0

    try:
        all_subs = session.query(Subscription).all()

        notified_users = set()
        for sub in all_subs:
            if sub.telegram_id in notified_users:
                continue
            # Точное совпадение ключа или ключ содержится в переданном key
            if sub.key == key or sub.key in key:
                try:
                    for part in split_message(message_text):
                        await bot.send_message(
                            sub.telegram_id,
                            part,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                    success_count += 1
                    notified_users.add(sub.telegram_id)
                except Exception as e:
                    print(f"Ошибка отправки пользователю {sub.telegram_id}: {e}")

        return success_count
    finally:
        session.close()


async def broadcast_message(message_text: str) -> dict:
    """Рассылка сообщения всем пользователям."""
    session = SessionLocal()
    stats = {"total": 0, "success": 0, "failed": 0}

    try:
        # Уникальные telegram_id
        tg_ids = session.query(Subscription.telegram_id).distinct().all()
        tg_ids = [row[0] for row in tg_ids]
        stats["total"] = len(tg_ids)

        for tg_id in tg_ids:
            try:
                for part in split_message(message_text):
                    await bot.send_message(
                        tg_id,
                        part,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                stats["success"] += 1
            except Exception as e:
                print(f"Ошибка отправки пользователю {tg_id}: {e}")
                stats["failed"] += 1

        return stats
    finally:
        session.close()


async def send_channel_post(text: str) -> None:
    for part in split_message(text):
        await bot.send_message(
            chat_id=BotConfig.CHANNEL_CHAT_ID,
            text=part,
            parse_mode='HTML',
            disable_web_page_preview=True,
            disable_notification=True
        )
