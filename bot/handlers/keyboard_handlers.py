from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
logger = logging.getLogger(__name__)

router = Router()

class buttons():
    builder = InlineKeyboardBuilder()

    builder.button(text="Показать уведомление", callback_data="show_alert")
    builder.button(text="Сменить это сообщение", callback_data="edit_message")
    builder.button(text="Сменить это сообщение обратно", callback_data="edit_message2")

buttons = buttons()

# Хэндлер на команду /start
@router.message(Command("start"))
async def cmd_start(message: types.message):

    await message.answer(
        "Привет! Я бот с клавиатурами.")


@router.message(Command("actions"))
async def cmd_actions(message: types.Message):
    
    
    await message.answer(
        "Нажми на кнопку, чтобы выполнить действие:",
        reply_markup=buttons.builder.as_markup()
    )

# Хэндлер для обработки нажатия на кнопку "Показать уведомление"
@router.callback_query(F.data == "show_alert")
async def handle_show_alert(callback: types.CallbackQuery):
    await callback.answer(
        "Это всплывающее уведомление!",
        show_alert=True # Делает уведомление модальным окном
    )

# Хэндлер для обработки нажатия на кнопку "Сменить это сообщение"
@router.callback_query(F.data == "edit_message")
async def handle_edit_message(callback: types.CallbackQuery):
    # Редактируем текст исходного сообщения
    try:
        await callback.message.edit_text(
            "ХАХАХАХАХ:",
            reply_markup=buttons.builder.as_markup()
        )
        await callback.answer()
    except TelegramBadRequest:
        await callback.answer()

@router.callback_query(F.data == "edit_message2")
async def handle_edit_message(callback: types.CallbackQuery):
    # Редактируем текст исходного сообщения
    await callback.message.edit_text(
        "Нажми на кнопку, чтобы выполнить действие:",
        reply_markup=buttons.builder.as_markup()
    )
    # Отвечаем на callback, чтобы убрать "часики" на кнопке
    await callback.answer()


