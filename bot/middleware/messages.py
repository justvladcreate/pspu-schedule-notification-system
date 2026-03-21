# [file name]: notifications.py
from .database import SessionLocal, User
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