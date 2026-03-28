from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.types import Message, ReplyKeyboardRemove
import logging
from ..middleware.database import SessionLocal, User
from ..middleware.utils import get_user_subscription
from config import BotConfig


logger = logging.getLogger(__name__)
router = Router()

def build_start_keyboard():
    kb_list = [
        [InlineKeyboardButton(text="Подписаться", callback_data="subscribe")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb_list)

def build_admins_keyboard():
    kb_list = [[KeyboardButton(text="Запустить парсер")]]
    return ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)

def build_subbed_keyboard():
    kb_list = [
        [InlineKeyboardButton(text="Изменить", callback_data="change"), InlineKeyboardButton(text="Отписаться", callback_data="unsubscribe")],
        [InlineKeyboardButton(text="Закрыть", callback_data="close")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb_list)

def build_category_keyboard():
    kb_list = [
        [InlineKeyboardButton(text="Преподаватель", callback_data="teacher"), InlineKeyboardButton(text="Группа", callback_data="group")],
        [InlineKeyboardButton(text="Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb_list)


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
        user_keyboard = build_subbed_keyboard()
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
        user_keyboard = build_start_keyboard()
    admin_keyboard = build_admins_keyboard()
    if message.from_user.id in BotConfig.ADMINS:
        await message.answer(text="Привет!", reply_markup=admin_keyboard, parse_mode='HTML')
    await message.answer(text=welcome_text, reply_markup=user_keyboard, parse_mode='HTML')





@router.callback_query(F.data == "subscribe")
async def choose_category(callback: types.CallbackQuery):
    try:
        keyboard = build_category_keyboard()
        await callback.message.edit_text(
            "Выберите категорию:",
            reply_markup=keyboard
        )
        await callback.answer(parse_mode='HTML')
    except TelegramBadRequest:
        await callback.answer(parse_mode='HTML')

@router.callback_query(F.data == "back")
async def back(callback: types.CallbackQuery):
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
    try:
        keyboard = build_start_keyboard()
        await callback.message.edit_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        await callback.answer(parse_mode='HTML')
    except TelegramBadRequest:
        await callback.answer(parse_mode='HTML')




