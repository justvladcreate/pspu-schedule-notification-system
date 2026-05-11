from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.command import Command
from aiogram.enums import ParseMode

from ..middleware.utils import (
    cache,
    get_available_letters,
    get_user_subscription,
)
from ..middleware.database import SessionLocal, User
from config import BotConfig

router = Router()
bot = BotConfig.BOT

PER_PAGE = 8

# -------- вспомогательные функции для клавиатур --------
def build_main_menu(tg_id: int):
    sub = get_user_subscription(tg_id)
    buttons = []
    if sub:
        buttons.append([InlineKeyboardButton(text="🔄 Изменить", callback_data="subscribe"),
                        InlineKeyboardButton(text="🗑️ Отписаться", callback_data="unsubscribe")])
    else:
        buttons.append([InlineKeyboardButton(text="➕ Подписаться", callback_data="subscribe")])
    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_category_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨‍🏫 Преподаватель", callback_data="cat_teachers"),
            InlineKeyboardButton(text="👥 Группа", callback_data="cat_groups"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

def build_alphabet_menu(letters):
    if not letters:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Нет преподавателей", callback_data="none")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_choice")]
        ])
    rows = []
    for i in range(0, len(letters), 6):
        row = [InlineKeyboardButton(text=l, callback_data=f"letter_{l}") for l in letters[i:i+6]]
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_choice")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_teachers_by_letter(teachers, letter, page, current_sub):
    filtered = [t for t in teachers if t.split()[0][0].upper() == letter.upper()]
    total = len(filtered)
    start = page * PER_PAGE
    end = start + PER_PAGE
    page_teachers = filtered[start:end]

    rows = []
    for teacher in page_teachers:
        is_current = (current_sub == teacher)
        text = f"✅ {teacher}" if is_current else teacher
        rows.append([InlineKeyboardButton(text=text, callback_data=f"teacher_{teacher}")])

    if total > PER_PAGE:
        total_pages = (total + PER_PAGE - 1) // PER_PAGE
        nav = [
            InlineKeyboardButton(text="⬅️", callback_data=f"page_teachers_{letter}_{(page - 1) % total_pages}"),
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="none"),
            InlineKeyboardButton(text="➡️", callback_data=f"page_teachers_{letter}_{(page + 1) % total_pages}"),
        ]
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_alphabet")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_groups_page(groups, page, current_sub):
    total = len(groups)
    start = page * PER_PAGE
    end = start + PER_PAGE
    page_groups = groups[start:end]

    rows = []
    for group in page_groups:
        is_current = (current_sub == group)
        text = f"✅ {group}" if is_current else group
        rows.append([InlineKeyboardButton(text=text, callback_data=f"group_{group}")])

    if total > PER_PAGE:
        total_pages = (total + PER_PAGE - 1) // PER_PAGE
        nav = [
            InlineKeyboardButton(text="⬅️", callback_data=f"page_groups_{(page - 1) % total_pages}"),
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="none"),
            InlineKeyboardButton(text="➡️", callback_data=f"page_groups_{(page + 1) % total_pages}"),
        ]
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_choice")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# -------- хранилище последнего меню для редактирования --------
user_last_menu = {}

async def replace_message(chat_id, text, markup):
    """Редактирует последнее сообщение бота в чате или отправляет новое"""
    if chat_id in user_last_menu:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_last_menu[chat_id],
                text=text,
                reply_markup=markup,
                parse_mode=ParseMode.HTML
            )
            return
        except Exception:
            try:
                await bot.delete_message(chat_id, user_last_menu[chat_id])
            except Exception:
                pass
    msg = await bot.send_message(chat_id, text, reply_markup=markup, parse_mode=ParseMode.HTML)
    user_last_menu[chat_id] = msg.message_id


# -------- обработчик команд --------
@router.message(Command("start"))
async def cmd_start(message: Message):
    chat_id = message.chat.id
    sub = get_user_subscription(message.from_user.id)
    if sub:
        text = f"👋 <b>Привет!</b>\n\n📌 Ваша подписка: <b>{sub}</b>\nВыберите действие:"
    else:
        text = ("👋 <b>Привет!</b> Я бот для уведомлений об изменениях в расписании.\n"
                "Вы можете подписаться на преподавателя или группу.")
    markup = build_main_menu(message.from_user.id)
    # Удалим предыдущее меню, если осталось
    if chat_id in user_last_menu:
        try:
            await bot.delete_message(chat_id, user_last_menu[chat_id])
        except:
            pass
    msg = await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    user_last_menu[chat_id] = msg.message_id


@router.message(Command("stop"))
async def cmd_stop(message: Message):
    chat_id = message.chat.id
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if user:
            old = user.key
            session.delete(user)
            session.commit()
            await message.answer(f"✅ Вы отписались от уведомлений для \"{old}\"")
        else:
            await message.answer("❌ Вы не были подписаны.")
    finally:
        session.close()
    if chat_id in user_last_menu:
        try:
            await bot.delete_message(chat_id, user_last_menu[chat_id])
        except:
            pass
        del user_last_menu[chat_id]


# -------- обработчик callback'ов --------
@router.callback_query()
async def callback_handler(call: CallbackQuery):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data
    current_sub = get_user_subscription(user_id)

    teachers = cache.get_teachers()
    groups = cache.get_groups()

    # Закрыть
    if data == "cancel":
        if chat_id in user_last_menu:
            try:
                await bot.delete_message(chat_id, user_last_menu[chat_id])
            except:
                pass
            del user_last_menu[chat_id]
        await call.answer()
        return

    if data == "none":
        await call.answer()
        return

    # Главное меню
    if data == "back_to_main":
        sub = get_user_subscription(user_id)
        text = f"👋 <b>Привет!</b>\n\n📌 Ваша подписка: <b>{sub}</b>\nВыберите действие:" if sub else "👋 <b>Привет!</b> Вы не подписаны.\nВыберите действие:"
        markup = build_main_menu(user_id)
        await replace_message(chat_id, text, markup)
        await call.answer()
        return

    # Подписаться / Изменить
    if data == "subscribe":
        markup = build_category_menu()
        await replace_message(chat_id, "Выберите категорию:", markup)
        await call.answer()
        return

    # Отписаться
    if data == "unsubscribe":
        session = SessionLocal()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                old = user.key
                session.delete(user)
                session.commit()
                text = f"✅ Отписались от <b>{old}</b>\nМожете подписаться заново."
            else:
                text = "❌ Нет активной подписки."
        finally:
            session.close()
        markup = build_main_menu(user_id)
        await replace_message(chat_id, text, markup)
        await call.answer()
        return

    # Категория: преподаватели
    if data == "cat_teachers":
        letters = get_available_letters(teachers)
        markup = build_alphabet_menu(letters)
        await replace_message(chat_id, "👨‍🏫 Выберите первую букву фамилии:", markup)
        await call.answer()
        return

    # Категория: группы
    if data == "cat_groups":
        markup = build_groups_page(groups, 0, current_sub)
        await replace_message(chat_id, "👥 Выберите группу:", markup)
        await call.answer()
        return

    # Назад к выбору категории
    if data == "back_to_choice":
        markup = build_category_menu()
        await replace_message(chat_id, "Выберите категорию:", markup)
        await call.answer()
        return

    # Назад к алфавиту
    if data == "back_to_alphabet":
        letters = get_available_letters(teachers)
        markup = build_alphabet_menu(letters)
        await replace_message(chat_id, "👨‍🏫 Выберите первую букву фамилии:", markup)
        await call.answer()
        return

    # Буква алфавита
    if data.startswith("letter_"):
        letter = data.split("_", 1)[1]
        markup = build_teachers_by_letter(teachers, letter, 0, current_sub)
        await replace_message(chat_id, f"👨‍🏫 Преподаватели на букву '{letter.upper()}':", markup)
        await call.answer()
        return

    # Пагинация преподавателей
    if data.startswith("page_teachers_"):
        _, _, letter, page_str = data.split("_", 3)
        page = int(page_str)
        markup = build_teachers_by_letter(teachers, letter.upper(), page, current_sub)
        await replace_message(chat_id, f"👨‍🏫 Преподаватели на букву '{letter.upper()}':", markup)
        await call.answer()
        return

    # Пагинация групп
    if data.startswith("page_groups_"):
        _, _, page_str = data.split("_", 2)
        page = int(page_str)
        markup = build_groups_page(groups, page, current_sub)
        await replace_message(chat_id, "👥 Выберите группу:", markup)
        await call.answer()
        return

    # Выбор преподавателя
    if data.startswith("teacher_"):
        chosen = data.replace("teacher_", "")
        session = SessionLocal()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            old = user.key if user else None
            if user:
                user.key = chosen
            else:
                user = User(telegram_id=user_id, key=chosen)
                session.add(user)
            session.commit()
        finally:
            session.close()
        text = f"✅ Подписались на преподавателя <b>{chosen}</b>" if old != chosen else f"❌ Вы уже подписаны на преподавателя <b>{chosen}</b>"
        markup = build_main_menu(user_id)
        await replace_message(chat_id, text, markup)
        await call.answer()
        return

    # Выбор группы
    if data.startswith("group_"):
        chosen = data.replace("group_", "")
        session = SessionLocal()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            old = user.key if user else None
            if user:
                user.key = chosen
            else:
                user = User(telegram_id=user_id, key=chosen)
                session.add(user)
            session.commit()
        finally:
            session.close()
        text = f"✅ Подписались на группу <b>{chosen}</b>" if old != chosen else f"❌ Вы уже подписаны на группу <b>{chosen}</b>"
        markup = build_main_menu(user_id)
        await replace_message(chat_id, text, markup)
        await call.answer()
        return

    await call.answer()