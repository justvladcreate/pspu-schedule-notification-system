from .database import SessionLocal, User, init_db

init_db()

def get_user_subscription(tg_id):
    """Получает текущую подписку пользователя"""
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(telegram_id=tg_id).first()
        return user.key if user else None
    finally:
        session.close()

def get_available_letters(teachers_list):
    """Получает список букв, для которых есть преподаватели"""
    letters_set = set()
    
    for teacher in teachers_list:
        if teacher.strip():
            parts = teacher.split()
            if parts:
                surname = parts[0]
                if surname:
                    first_letter = surname[0].upper()
                    letters_set.add(first_letter)
    
    return sorted(letters_set)