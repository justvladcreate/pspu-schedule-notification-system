from .database import SessionLocal, Subscription, MAX_SUBSCRIPTIONS, init_db

init_db()


def get_user_subscriptions(tg_id):
    """Получает все подписки пользователя"""
    session = SessionLocal()
    try:
        subs = session.query(Subscription).filter_by(telegram_id=tg_id).all()
        return [{"key": s.key, "type": s.type, "id": s.id} for s in subs]
    finally:
        session.close()


def get_user_subscription(tg_id):
    """Обратная совместимость — возвращает первый ключ"""
    subs = get_user_subscriptions(tg_id)
    return subs[0]["key"] if subs else None


def add_subscription(tg_id, key, sub_type):
    """Добавляет подписку. Возвращает (success, message)"""
    session = SessionLocal()
    try:
        count = session.query(Subscription).filter_by(telegram_id=tg_id).count()
        if count >= MAX_SUBSCRIPTIONS:
            return False, f"Максимум {MAX_SUBSCRIPTIONS} подписок"

        existing = session.query(Subscription).filter_by(
            telegram_id=tg_id, key=key
        ).first()
        if existing:
            return False, "Вы уже подписаны на это"

        sub = Subscription(telegram_id=tg_id, key=key, type=sub_type)
        session.add(sub)
        session.commit()
        return True, "Подписка добавлена"
    finally:
        session.close()


def remove_subscription(tg_id, sub_id):
    """Удаляет подписку по id"""
    session = SessionLocal()
    try:
        sub = session.query(Subscription).filter_by(
            id=sub_id, telegram_id=tg_id
        ).first()
        if sub:
            session.delete(sub)
            session.commit()
            return True
        return False
    finally:
        session.close()


def remove_all_subscriptions(tg_id):
    """Удаляет все подписки пользователя"""
    session = SessionLocal()
    try:
        session.query(Subscription).filter_by(telegram_id=tg_id).delete()
        session.commit()
    finally:
        session.close()


def get_available_letters(teachers_list):
    """Получает список букв, для которых есть преподаватели"""
    letters_set = set()
    for teacher in teachers_list:
        if teacher.strip():
            parts = teacher.split()
            if parts:
                first_letter = parts[0][0].upper()
                letters_set.add(first_letter)
    return sorted(letters_set)
