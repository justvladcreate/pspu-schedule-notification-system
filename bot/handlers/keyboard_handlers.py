from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
from datetime import date

from ..middleware.database import SessionLocal, Subscription, MAX_SUBSCRIPTIONS
from ..middleware.utils import (
    get_user_subscriptions, add_subscription,
    remove_subscription, remove_all_subscriptions
)
from parser.process import get_cached_schedule
from parser.date_parser import get_active_lesson, get_lesson_end_time
from config import BotConfig

logger = logging.getLogger(__name__)
router = Router()

DAY_MAP = {
    0: "ПОНЕДЕЛЬНИК", 1: "ВТОРНИК", 2: "СРЕДА",
    3: "ЧЕТВЕРГ", 4: "ПЯТНИЦА", 5: "СУББОТА", 6: "ВОСКРЕСЕНЬЕ"
}
DAY_SHORT = {
    0: "ПН", 1: "ВТ", 2: "СР", 3: "ЧТ", 4: "ПТ", 5: "СБ", 6: "ВС"
}


class SubscribeStates(StatesGroup):
    waiting_teacher_name = State()


# ── Клавиатуры ──

def build_main_keyboard(subs):
    """Главное меню"""
    buttons = []
    if subs:
        buttons.append([InlineKeyboardButton(text="📋 Мои подписки", callback_data="my_subs")])
        buttons.append([InlineKeyboardButton(text="📅 Расписание на сегодня", callback_data="today_schedule")])
    if len(subs) < MAX_SUBSCRIPTIONS:
        buttons.append([InlineKeyboardButton(text="➕ Подписаться", callback_data="subscribe")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_category_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Группа", callback_data="cat_group"),
         InlineKeyboardButton(text="👨‍🏫 Преподаватель", callback_data="cat_teacher")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])


def build_groups_keyboard(groups, page=0, page_size=10):
    """Клавиатура выбора группы с пагинацией"""
    sorted_groups = sorted(groups)
    total_pages = (len(sorted_groups) + page_size - 1) // page_size
    start = page * page_size
    end = start + page_size
    page_groups = sorted_groups[start:end]

    buttons = []
    row = []
    for g in page_groups:
        row.append(InlineKeyboardButton(text=g, callback_data=f"grp_{g}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Навигация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"grp_page_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"grp_page_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="subscribe")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_teacher_letters_keyboard(teachers):
    """Клавиатура с буквами фамилий преподавателей"""
    letters = set()
    for t in teachers:
        if t.strip():
            first = t.strip()[0].upper()
            if first.isalpha():
                letters.add(first)

    sorted_letters = sorted(letters)
    buttons = []
    row = []
    for letter in sorted_letters:
        row.append(InlineKeyboardButton(text=letter, callback_data=f"tletter_{letter}"))
        if len(row) == 6:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🔍 Ввести вручную", callback_data="teacher_manual")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="subscribe")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_teachers_by_letter_keyboard(teachers, letter, page=0, page_size=8):
    """Список преподавателей на букву"""
    filtered = sorted(set(t for t in teachers if t.strip() and t.strip()[0].upper() == letter))
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    start = page * page_size
    page_teachers = filtered[start:start + page_size]

    buttons = []
    for t in page_teachers:
        short = t[:30] + "..." if len(t) > 30 else t
        buttons.append([InlineKeyboardButton(text=short, callback_data=f"tch_{t}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"tpage_{letter}_{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"tpage_{letter}_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="cat_teacher")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_subs_keyboard(subs):
    """Список подписок пользователя"""
    buttons = []
    for s in subs:
        icon = "👥" if s["type"] == "group" else "👨‍🏫"
        buttons.append([
            InlineKeyboardButton(text=f"{icon} {s['key']}", callback_data=f"sub_info_{s['id']}"),
            InlineKeyboardButton(text="❌", callback_data=f"unsub_{s['id']}")
        ])

    if len(subs) < MAX_SUBSCRIPTIONS:
        buttons.append([InlineKeyboardButton(text="➕ Добавить", callback_data="subscribe")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Утилиты ──

def get_all_groups():
    """Получает список всех групп из кэша"""
    schedule = get_cached_schedule()
    if schedule:
        return list(schedule.keys())
    return []


def get_all_teachers():
    """Получает список всех преподавателей из кэша"""
    schedule = get_cached_schedule()
    if not schedule:
        return []
    teachers = set()
    for group_data in schedule.values():
        for t in group_data.get("teachers", []):
            val = t.get("value", "")
            for name in val.split(","):
                name = name.strip()
                if name:
                    teachers.add(name)
    return sorted(teachers)


def _clean_time(time_val):
    """Убирает день недели из строки времени"""
    clean = time_val
    for day in list(DAY_MAP.values()) + list(DAY_SHORT.values()):
        clean = clean.replace(day, "").strip()
    return clean


def _get_val(item):
    """Извлекает value из dict или возвращает строку"""
    return item["value"] if isinstance(item, dict) else item


def format_today_schedule(group_name):
    """Формирует расписание на сегодня для группы"""
    schedule = get_cached_schedule()
    if not schedule or group_name not in schedule:
        return f"Расписание для группы {group_name} не найдено."

    data = schedule[group_name]
    today = date.today()
    today_day = DAY_MAP.get(today.weekday(), "")
    today_short = DAY_SHORT.get(today.weekday(), "")

    times = data.get("times", [])
    raw_subjects = data.get("raw_subjects", data.get("subjects", []))
    rooms = data.get("rooms", [])
    event_flags = data.get("event_flags", [False] * len(times))

    lines = [f"📅 <b>Расписание на сегодня — {today_day}</b>", f"👥 Группа: <b>{group_name}</b>", ""]

    found = False
    for i, (time_item, raw_subj_item, room_item) in enumerate(zip(times, raw_subjects, rooms)):
        time_val = _get_val(time_item)
        raw_subj = _get_val(raw_subj_item)
        room_val = _get_val(room_item)

        # Проверяем день недели
        if today_day not in time_val.upper() and today_short not in time_val.upper():
            continue

        # Для событий показываем как есть
        is_event = event_flags[i] if i < len(event_flags) else False

        # Получаем активный предмет с правильным преподавателем
        lesson = get_active_lesson(raw_subj, room_val, today)

        if not lesson["subject"] and not is_event:
            continue

        clean_time = _clean_time(time_val)
        end_time = get_lesson_end_time(time_val)
        time_display = f"{clean_time} - {end_time}" if end_time else clean_time

        found = True
        lines.append(f"🕐 <b>{time_display}</b>")
        if is_event:
            lines.append(f"   📢 {lesson['subject'] or raw_subj}")
        else:
            lines.append(f"   📖 {lesson['subject']}")
        if lesson["teacher"]:
            lines.append(f"   👨‍🏫 {lesson['teacher']}")
        if lesson["room"]:
            lines.append(f"   🚪 {lesson['room']}")
        lines.append("")

    if not found:
        lines.append("Пар нет! 🎉")

    return "\n".join(lines)


def format_teacher_schedule(teacher_name):
    """Формирует расписание преподавателя на сегодня"""
    schedule = get_cached_schedule()
    if not schedule:
        return "Расписание не загружено."

    today = date.today()
    today_day = DAY_MAP.get(today.weekday(), "")
    today_short = DAY_SHORT.get(today.weekday(), "")

    lines = [f"📅 <b>Расписание на сегодня — {today_day}</b>", f"👨‍🏫 Преподаватель: <b>{teacher_name}</b>", ""]

    found = False
    for group_name, data in schedule.items():
        times = data.get("times", [])
        raw_subjects = data.get("raw_subjects", data.get("subjects", []))
        rooms = data.get("rooms", [])

        for i, (time_item, raw_subj_item, room_item) in enumerate(zip(times, raw_subjects, rooms)):
            time_val = _get_val(time_item)
            raw_subj = _get_val(raw_subj_item)
            room_val = _get_val(room_item)

            # Проверяем день
            if today_day not in time_val.upper() and today_short not in time_val.upper():
                continue

            # Получаем активный урок
            lesson = get_active_lesson(raw_subj, room_val, today)

            # Проверяем что этот преподаватель ведёт этот урок
            if not lesson["teacher"] or teacher_name.lower() not in lesson["teacher"].lower():
                continue

            clean_time = _clean_time(time_val)
            end_time = get_lesson_end_time(time_val)
            time_display = f"{clean_time} - {end_time}" if end_time else clean_time

            found = True
            lines.append(f"🕐 <b>{time_display}</b>")
            lines.append(f"   📖 {lesson['subject']}")
            lines.append(f"   👥 Группа: {group_name}")
            if lesson["room"]:
                lines.append(f"   🚪 {lesson['room']}")
            lines.append("")

    if not found:
        lines.append("Пар нет! 🎉")

    return "\n".join(lines)


# ── Хэндлеры ──

def _build_admin_kb():
    from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Запустить парсер"), KeyboardButton(text="Тест уведомлений")],
            [KeyboardButton(text="Меню")]
        ],
        resize_keyboard=True, one_time_keyboard=False
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in BotConfig.ADMINS:
        return
    await message.answer("Панель администратора:", reply_markup=_build_admin_kb())


@router.message(F.text == "Меню")
async def btn_menu(message: Message, state: FSMContext):
    """Кнопка Меню — показывает главное меню с подписками"""
    await state.clear()
    subs = get_user_subscriptions(message.from_user.id)
    welcome = "Главное меню:"
    if subs:
        sub_list = "\n".join(f"  {'👥' if s['type'] == 'group' else '👨‍🏫'} {s['key']}" for s in subs)
        welcome += f"\n\n📋 <b>Подписки:</b>\n{sub_list}"
    await message.answer(welcome, reply_markup=build_main_keyboard(subs), parse_mode='HTML')


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    subs = get_user_subscriptions(message.from_user.id)

    if message.from_user.id in BotConfig.ADMINS:
        await message.answer("Панель администратора:", reply_markup=_build_admin_kb())

    welcome = (
        "👋 <b>Привет!</b> Я бот для уведомлений об изменениях в расписании ПСПУ.\n\n"
        "Подпишись на группу или преподавателя, и я буду присылать тебе изменения."
    )
    if subs:
        sub_list = "\n".join(f"  {'👥' if s['type'] == 'group' else '👨‍🏫'} {s['key']}" for s in subs)
        welcome += f"\n\n📋 <b>Твои подписки:</b>\n{sub_list}"

    await message.answer(welcome, reply_markup=build_main_keyboard(subs), parse_mode='HTML')


@router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    """Быстрая команда — расписание на сегодня"""
    subs = get_user_subscriptions(message.from_user.id)
    if not subs:
        await message.answer("У тебя нет подписок. Используй /start чтобы подписаться.")
        return

    for s in subs:
        if s["type"] == "group":
            text = format_today_schedule(s["key"])
        else:
            text = format_teacher_schedule(s["key"])
        await message.answer(text, parse_mode='HTML')


# ── Callback handlers ──

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    subs = get_user_subscriptions(callback.from_user.id)
    welcome = "Главное меню:"
    if subs:
        sub_list = "\n".join(f"  {'👥' if s['type'] == 'group' else '👨‍🏫'} {s['key']}" for s in subs)
        welcome += f"\n\n📋 <b>Подписки:</b>\n{sub_list}"
    try:
        await callback.message.edit_text(welcome, reply_markup=build_main_keyboard(subs), parse_mode='HTML')
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data == "subscribe")
async def choose_category(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "Выберите категорию подписки:",
            reply_markup=build_category_keyboard()
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


# ── Подписка на группу ──

@router.callback_query(F.data == "cat_group")
async def show_groups(callback: CallbackQuery):
    groups = get_all_groups()
    if not groups:
        await callback.answer("Группы ещё не загружены. Дождитесь первого парсинга.", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            "Выберите группу:",
            reply_markup=build_groups_keyboard(groups, page=0)
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("grp_page_"))
async def groups_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    groups = get_all_groups()
    try:
        await callback.message.edit_text(
            "Выберите группу:",
            reply_markup=build_groups_keyboard(groups, page=page)
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("grp_") & ~F.data.startswith("grp_page_"))
async def subscribe_group(callback: CallbackQuery):
    group_name = callback.data[4:]
    success, msg = add_subscription(callback.from_user.id, group_name, "group")

    if success:
        await callback.answer(f"✅ Подписка на группу {group_name} добавлена!", show_alert=True)
    else:
        await callback.answer(f"⚠️ {msg}", show_alert=True)

    # Возврат в главное меню
    subs = get_user_subscriptions(callback.from_user.id)
    try:
        sub_list = "\n".join(f"  {'👥' if s['type'] == 'group' else '👨‍🏫'} {s['key']}" for s in subs)
        await callback.message.edit_text(
            f"Главное меню:\n\n📋 <b>Подписки:</b>\n{sub_list}",
            reply_markup=build_main_keyboard(subs),
            parse_mode='HTML'
        )
    except TelegramBadRequest:
        pass


# ── Подписка на преподавателя ──

@router.callback_query(F.data == "cat_teacher")
async def show_teacher_letters(callback: CallbackQuery):
    teachers = get_all_teachers()
    if not teachers:
        await callback.answer("Преподаватели ещё не загружены. Дождитесь первого парсинга.", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            "Выберите первую букву фамилии преподавателя:",
            reply_markup=build_teacher_letters_keyboard(teachers)
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("tletter_"))
async def show_teachers_by_letter(callback: CallbackQuery):
    letter = callback.data.split("_")[1]
    teachers = get_all_teachers()
    try:
        await callback.message.edit_text(
            f"Преподаватели на '{letter}':",
            reply_markup=build_teachers_by_letter_keyboard(teachers, letter)
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("tpage_"))
async def teachers_pagination(callback: CallbackQuery):
    parts = callback.data.split("_")
    letter = parts[1]
    page = int(parts[2])
    teachers = get_all_teachers()
    try:
        await callback.message.edit_text(
            f"Преподаватели на '{letter}':",
            reply_markup=build_teachers_by_letter_keyboard(teachers, letter, page)
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("tch_"))
async def subscribe_teacher(callback: CallbackQuery):
    teacher_name = callback.data[4:]
    success, msg = add_subscription(callback.from_user.id, teacher_name, "teacher")

    if success:
        await callback.answer(f"✅ Подписка на {teacher_name} добавлена!", show_alert=True)
    else:
        await callback.answer(f"⚠️ {msg}", show_alert=True)

    subs = get_user_subscriptions(callback.from_user.id)
    try:
        sub_list = "\n".join(f"  {'👥' if s['type'] == 'group' else '👨‍🏫'} {s['key']}" for s in subs)
        await callback.message.edit_text(
            f"Главное меню:\n\n📋 <b>Подписки:</b>\n{sub_list}",
            reply_markup=build_main_keyboard(subs),
            parse_mode='HTML'
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "teacher_manual")
async def teacher_manual_input(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text(
            "Введите ФИО преподавателя в формате:\n<i>Иванов И.И.</i> или <i>Иванов И И</i>",
            parse_mode='HTML'
        )
    except TelegramBadRequest:
        pass
    await state.set_state(SubscribeStates.waiting_teacher_name)
    await callback.answer()


@router.message(SubscribeStates.waiting_teacher_name)
async def process_teacher_name(message: Message, state: FSMContext):
    teacher_name = message.text.strip()
    success, msg = add_subscription(message.from_user.id, teacher_name, "teacher")

    if success:
        text = f"✅ Подписка на {teacher_name} добавлена!"
    else:
        text = f"⚠️ {msg}"

    await state.clear()
    subs = get_user_subscriptions(message.from_user.id)
    await message.answer(text, reply_markup=build_main_keyboard(subs), parse_mode='HTML')


# ── Управление подписками ──

@router.callback_query(F.data == "my_subs")
async def show_my_subs(callback: CallbackQuery):
    subs = get_user_subscriptions(callback.from_user.id)
    if not subs:
        await callback.answer("У вас нет подписок.", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            f"📋 <b>Ваши подписки</b> ({len(subs)}/{MAX_SUBSCRIPTIONS}):\n\n"
            "Нажмите ❌ чтобы отписаться:",
            reply_markup=build_subs_keyboard(subs),
            parse_mode='HTML'
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("unsub_"))
async def unsubscribe(callback: CallbackQuery):
    sub_id = int(callback.data.split("_")[1])
    success = remove_subscription(callback.from_user.id, sub_id)

    if success:
        await callback.answer("✅ Подписка удалена!", show_alert=True)
    else:
        await callback.answer("⚠️ Подписка не найдена.", show_alert=True)

    subs = get_user_subscriptions(callback.from_user.id)
    if subs:
        try:
            await callback.message.edit_text(
                f"📋 <b>Ваши подписки</b> ({len(subs)}/{MAX_SUBSCRIPTIONS}):\n\n"
                "Нажмите ❌ чтобы отписаться:",
                reply_markup=build_subs_keyboard(subs),
                parse_mode='HTML'
            )
        except TelegramBadRequest:
            pass
    else:
        try:
            await callback.message.edit_text(
                "У вас больше нет подписок.",
                reply_markup=build_main_keyboard([]),
                parse_mode='HTML'
            )
        except TelegramBadRequest:
            pass


# ── Расписание на сегодня ──

@router.callback_query(F.data == "today_schedule")
async def show_today_schedule(callback: CallbackQuery):
    subs = get_user_subscriptions(callback.from_user.id)
    if not subs:
        await callback.answer("Нет подписок.", show_alert=True)
        return

    await callback.answer()

    for s in subs:
        if s["type"] == "group":
            text = format_today_schedule(s["key"])
        else:
            text = format_teacher_schedule(s["key"])
        await callback.message.answer(text, parse_mode='HTML')


# ── Инфо о подписке ──

@router.callback_query(F.data.startswith("sub_info_"))
async def sub_info(callback: CallbackQuery):
    sub_id = int(callback.data.split("_")[-1])
    session = SessionLocal()
    try:
        sub = session.query(Subscription).filter_by(
            id=sub_id, telegram_id=callback.from_user.id
        ).first()
        if not sub:
            await callback.answer("Подписка не найдена.", show_alert=True)
            return

        if sub.type == "group":
            text = format_today_schedule(sub.key)
        else:
            text = format_teacher_schedule(sub.key)
        await callback.message.answer(text, parse_mode='HTML')
        await callback.answer()
    finally:
        session.close()
