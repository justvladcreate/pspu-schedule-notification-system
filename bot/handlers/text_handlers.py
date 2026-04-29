from aiogram import Router, F
from aiogram.types import Message
from ..middleware.utils import normalize_key, get_user_subscription
from ..middleware.database import SessionLocal, User

router = Router()

@router.message(F.text)
async def text_input(message: Message):
    chat_id = message.chat.id
    key = normalize_key(message.text)
    if len(key) < 2:
        await message.answer("❌ Слишком короткий запрос. Введите ФИО или номер группы.")
        return

    session = SessionLocal()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        old = user.key if user else None
        if user:
            user.key = key
        else:
            user = User(telegram_id=message.from_user.id, key=key)
            session.add(user)
        session.commit()
    finally:
        session.close()

    if old == key:
        resp = f"❌ Вы уже подписаны на \"{key}\""
    elif old:
        resp = f"✅ Изменили подписку:\n\"{old}\" → \"{key}\""
    else:
        resp = f"✅ Подписались на \"{key}\""
    await message.answer(resp)

