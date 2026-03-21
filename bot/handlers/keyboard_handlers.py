from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
logger = logging.getLogger(__name__)
from ..middleware.database import SessionLocal, User
from ..middleware.utils import get_user_subscription

router = Router()

def build_start_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Подписаться", callback_data="subscribe")
    return keyboard

def build_subbed_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Изменить", callback_data="change")
    keyboard.button(text="Отписаться", callback_data="unsubscribe")
    keyboard.button(text="Закрыть", callback_data="close")
    return keyboard

def build_category_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Преподаватель", callback_data="teacher")
    keyboard.button(text="Группа", callback_data="group")
    keyboard.button(text="Назад", callback_data="back")
    return keyboard


# Хэндлер на команду /start
@router.message(Command("start"))
async def cmd_start(message: types.message):

    # Получаем данные пользователя
    subscription = get_user_subscription(message.from_user.id)
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    session.close()
    
    if user:
        welcome_text = "haha"
        keyboard = build_subbed_keyboard()
    else:
        welcome_text = (
                "👋 <b>Привет!</b> Я бот для уведомлений об изменениях в расписании.\n\n"
                "Вы можете:\n"
                "• Ввести ФИО преподавателя или номер группы\n"
                "• Использовать меню для выбора из списка\n\n"
                "📝 <b>Формат ввода:</b>\n"
                "- Для преподавателей: <i>Иванов И.И.</i> или <i>Иванов И И</i>\n"
                "- Для групп: <i>1227</i> или <i>М1217</i>\n\n"
                "Используйте меню ниже для управления подпиской:"
            )
        keyboard = build_start_keyboard()
    await message.answer(welcome_text, reply_markup=keyboard.as_markup())


@router.callback_query(F.data == "subscribe")
async def handle_show_alert(callback: types.CallbackQuery):
    try:
        keyboard = build_category_keyboard()
        await callback.message.edit_text(
            "Выберите категорию:",
            reply_markup=keyboard.as_markup()
        )
        await callback.answer()
    except TelegramBadRequest:
        await callback.answer()



