# bot/notifier.py
import json
import os
from collections import defaultdict
from difflib import SequenceMatcher
from typing import List, Dict, Any, Set

from config import BotConfig
from bot.middleware.database import SessionLocal, User

bot = BotConfig.BOT
CHANNEL_CHAT_ID = BotConfig.CHANNEL_CHAT_ID   # добавлено

SCHEDULE_JSON_PATH = "data/latest/groups_info_parsed.json"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1_fsm-OxH9E9LgHnLC0iju5OlaHIv0agmM87GLvRKIAg/edit"


def load_full_events() -> Dict[str, Dict]:
    if not os.path.exists(SCHEDULE_JSON_PATH):
        return {}
    try:
        with open(SCHEDULE_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        events = data.get('events', [])
        return {ev['event_id']: ev for ev in events}
    except (json.JSONDecodeError, KeyError):
        return {}


def escape_html(text: str) -> str:
    if not text:
        return ""
    return (text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def extract_teachers_set(teachers_data) -> Set[str]:
    if not teachers_data:
        return set()
    if isinstance(teachers_data, list):
        return {t.strip() for t in teachers_data if t and t.strip()}
    if isinstance(teachers_data, str):
        return {t.strip() for t in teachers_data.split(',') if t.strip()}
    return set()


def is_user_affected(user_key: str, change: Dict, full_events: Dict) -> bool:
    event_id = change.get('event_id')
    group = change.get('group', '')
    if user_key == group:
        return True

    teachers_set = set()
    if change['change_type'] in ('added', 'removed'):
        teachers_data = change.get('data', {}).get('teachers', '')
        teachers_set = extract_teachers_set(teachers_data)
    else:
        full = full_events.get(event_id, {})
        teachers_data = full.get('teachers', '')
        teachers_set = extract_teachers_set(teachers_data)
        for field in change.get('changes', []):
            if field['field'] == 'teachers':
                old_set = extract_teachers_set(field['old_value'])
                new_set = extract_teachers_set(field['new_value'])
                teachers_set.update(old_set, new_set)
    return user_key in teachers_set


def format_field_change(field: str, old_value: str, new_value: str) -> str:
    field_names = {
        'discipline': 'Дисциплина',
        'type': 'Тип',
        'subgroup': 'Подгруппа',
        'teachers': 'Преподаватель',
        'dates': 'Даты',
        'rooms': 'Аудитория',
        'comment': 'Комментарий'
    }
    field_name = field_names.get(field, field.capitalize())

    old_clean = old_value.strip() if old_value else ''
    new_clean = new_value.strip() if new_value else ''

    if not new_clean and old_clean:
        return f"{field_name}: ❌ {escape_html(old_clean)}"
    if not old_clean and new_clean:
        return f"{field_name}: ✅ {escape_html(new_clean)}"

    if old_clean != new_clean:
        if field == 'teachers':
            # Логика для преподавателей остаётся как была (точечные изменения)
            old_set = {t.strip() for t in old_clean.split(',') if t.strip()}
            new_set = {t.strip() for t in new_clean.split(',') if t.strip()}
            removed = old_set - new_set
            added = new_set - old_set
            if removed and added:
                parts = []
                if removed:
                    parts.append(f"❌ {', '.join(sorted(removed))}")
                if added:
                    parts.append(f"✅ {', '.join(sorted(added))}")
                return f"{field_name}: {'; '.join(parts)}"
            elif removed:
                return f"{field_name}: ❌ {', '.join(sorted(removed))}"
            elif added:
                return f"{field_name}: ✅ {', '.join(sorted(added))}"
            else:
                # Если замена один-в-один, выделяем изменённую часть
                highlighted = highlight_changes(old_clean, new_clean)
                return f"{field_name}: ⚠️ {escape_html(old_clean)} → {highlighted}"
        else:
            # Для всех остальных полей выделяем только изменённую часть
            highlighted = highlight_changes(old_clean, new_clean)
            return f"{field_name}: ⚠️ {escape_html(old_clean)} → {highlighted}"
    return ""

def highlight_changes(old: str, new: str) -> str:
    if not old and not new:
        return ""
    if not old:
        return f"<b>{escape_html(new)}</b>"
    if not new:
        return ""
    sm = SequenceMatcher(None, old, new)
    result = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            result.append(escape_html(new[j1:j2]))
        elif tag in ("replace", "insert"):
            result.append(f"<b>{escape_html(new[j1:j2])}</b>")
        # delete игнорируем
    return "".join(result)

def build_event_header(event: Dict, time_str: str, weekday: str) -> str:
    discipline = event.get('discipline', '') or ''
    discipline = discipline.strip() if isinstance(discipline, str) else ''
    type_ = event.get('type', '') or ''
    type_ = type_.strip() if isinstance(type_, str) else ''
    subgroup = event.get('subgroup', '') or ''
    subgroup = subgroup.strip() if isinstance(subgroup, str) else ''

    parts = []
    if discipline:
        parts.append(discipline)
    if type_:
        parts.append(f"({type_})")
    if subgroup:
        parts.append(f"подгр. {subgroup}")

    # Подчёркивание времени
    time_part = f"{weekday} {time_str}" if weekday and time_str else (time_str or "Время не указано")
    header = f"<u>{time_part}</u>"
    if parts:
        header += f" - {', '.join(parts)}"
    return f"   {header}"


def format_event_summary(event: Dict, include_label: bool = True) -> str:
    discipline = event.get('discipline', '') or ''
    discipline = discipline.strip() if isinstance(discipline, str) else ''
    type_ = event.get('type', '') or ''
    type_ = type_.strip() if isinstance(type_, str) else ''
    subgroup = event.get('subgroup', '') or ''
    subgroup = subgroup.strip() if isinstance(subgroup, str) else ''

    teachers_raw = event.get('teachers', [])
    if isinstance(teachers_raw, list):
        teachers = ', '.join(teachers_raw)
    else:
        teachers = str(teachers_raw).strip() if teachers_raw else ''

    rooms = event.get('rooms', '') or ''
    rooms = rooms.strip() if isinstance(rooms, str) else ''
    dates = event.get('dates', '') or ''
    dates = dates.strip() if isinstance(dates, str) else ''

    parts = []
    if discipline:
        parts.append(discipline)
    if type_:
        parts.append(f"({type_})")
    if subgroup:
        parts.append(f"подгр. {subgroup}")
    if teachers:
        parts.append(f"преп. {teachers}")
    if rooms:
        parts.append(f"ауд. {rooms}")
    if dates:
        parts.append(f"даты: {dates}")

    return ", ".join(parts) if parts else "Неизвестное занятие"


def build_teacher_message(user_key: str, events_dict: Dict[str, Dict]) -> str:
    groups_events = defaultdict(list)
    for event_id, ev_data in events_dict.items():
        group = ev_data['full_event'].get('group', 'Без группы')
        groups_events[group].append((event_id, ev_data))

    lines = [f"<b>[{escape_html(user_key)}]</b>", ""]

    for group_name in sorted(groups_events.keys()):
        lines.append(f"• <b>[{escape_html(group_name)}]</b>")
        events_list = groups_events[group_name]
        events_list.sort(key=lambda kv: (kv[1]['order'], kv[1]['pair_number']))

        for event_id, ev_data in events_list:
            full = ev_data['full_event']
            header = build_event_header(full, ev_data['time'], ev_data['weekday'])
            lines.append(header)

            if ev_data['type'] == 'added':
                lines.append(f"      ✅ {format_event_summary(full, include_label=False)}")
            elif ev_data['type'] == 'removed':
                lines.append(f"      ❌ {format_event_summary(full, include_label=False)}")
            else:  # changed
                for field_change in ev_data['changes']:
                    line = format_field_change(
                        field_change['field'],
                        field_change['old_value'],
                        field_change['new_value']
                    )
                    if line:
                        lines.append(f"      {line}")
            lines.append("")
        lines.append("")

    lines.append(f"📄 <a href='{SPREADSHEET_URL}'>Открыть расписание</a>")
    return "\n".join(lines).strip()


def build_group_message(user_key: str, events_dict: Dict[str, Dict]) -> str:
    lines = [f"<b>[{escape_html(user_key)}]</b>", ""]
    sorted_events = sorted(events_dict.items(), key=lambda kv: (kv[1]['order'], kv[1]['pair_number']))
    for event_id, ev_data in sorted_events:
        full = ev_data['full_event']
        header = build_event_header(full, ev_data['time'], ev_data['weekday'])
        lines.append(header)

        if ev_data['type'] == 'added':
            lines.append(f"   ✅ {format_event_summary(full, include_label=False)}")
        elif ev_data['type'] == 'removed':
            lines.append(f"   ❌ {format_event_summary(full, include_label=False)}")
        else:
            for field_change in ev_data['changes']:
                line = format_field_change(
                    field_change['field'],
                    field_change['old_value'],
                    field_change['new_value']
                )
                if line:
                    lines.append(f"   {line}")
        lines.append("")
    lines.append(f"📄 <a href='{SPREADSHEET_URL}'>Открыть расписание</a>")
    return "\n".join(lines).strip()

def build_channel_message(changes: List[Dict], full_events: Dict) -> str:
    """Формирует сообщение для общего канала, группируя изменения по группам."""
    # Агрегируем изменения по group_name и event_id
    groups_data = defaultdict(lambda: defaultdict(dict))  # group_name -> event_id -> ev_data

    for change in changes:
        event_id = change.get('event_id')
        if not event_id:
            continue
        group = change.get('group', '')
        if not group:
            continue

        ev_data = groups_data[group][event_id]
        if 'weekday' not in ev_data:
            ev_data['weekday'] = change.get('weekday', '')
            ev_data['time'] = change.get('time', '')
            ev_data['pair_number'] = change.get('pair_number', 0)
            weekday_order = {"ПН": 1, "ВТ": 2, "СР": 3, "ЧТ": 4, "ПТ": 5, "СБ": 6, "ВС": 7}
            ev_data['order'] = weekday_order.get(ev_data['weekday'], 99)
            ev_data['type'] = change['change_type']

            if change['change_type'] in ('added', 'removed'):
                ev_data['full_event'] = change.get('data', {})
            else:
                ev_data['full_event'] = full_events.get(event_id, {})
                ev_data['changes'] = ev_data.get('changes', [])
                existing_fields = {ch['field'] for ch in ev_data['changes']}
                for field_change in change.get('changes', []):
                    if field_change['field'] not in existing_fields:
                        ev_data['changes'].append(field_change)

    lines = ["<b>📢 Изменения в расписании</b>", ""]

    for group_name in sorted(groups_data.keys()):
        lines.append(f"<b>[{escape_html(group_name)}]</b>")
        events_dict = groups_data[group_name]
        sorted_events = sorted(events_dict.items(), key=lambda kv: (kv[1]['order'], kv[1]['pair_number']))

        for event_id, ev_data in sorted_events:
            full = ev_data['full_event']
            header = build_event_header(full, ev_data['time'], ev_data['weekday'])
            lines.append(header)

            if ev_data['type'] == 'added':
                lines.append(f"   ✅ {format_event_summary(full, include_label=False)}")
            elif ev_data['type'] == 'removed':
                lines.append(f"   ❌ {format_event_summary(full, include_label=False)}")
            else:  # changed
                for field_change in ev_data['changes']:
                    line = format_field_change(
                        field_change['field'],
                        field_change['old_value'],
                        field_change['new_value']
                    )
                    if line:
                        lines.append(f"   {line}")
            lines.append("")
        lines.append("")

    lines.append(f"📄 <a href='{SPREADSHEET_URL}'>Открыть расписание</a>")
    return "\n".join(lines).strip()

async def send_notifications(changes: List[Dict[str, Any]]) -> None:
    if not changes:
        return

    full_events = load_full_events()

    # --- Отправка в канал (общее сообщение) ---
    channel_message = build_channel_message(changes, full_events)
    if channel_message:
        try:
            await bot.send_message(
                CHANNEL_CHAT_ID,
                channel_message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"[NOTIFIER] Ошибка отправки в канал: {e}")

    # --- Отправка пользователям ---
    session = SessionLocal()
    try:
        users = session.query(User).all()
        if not users:
            return
    finally:
        session.close()

    user_changes: Dict[int, Dict[str, Dict]] = defaultdict(lambda: defaultdict(dict))

    for change in changes:
        event_id = change.get('event_id')
        if not event_id:
            continue

        affected_users = []
        for user in users:
            if is_user_affected(user.key, change, full_events):
                affected_users.append(user)

        for user in affected_users:
            ev_data = user_changes[user.telegram_id][event_id]
            if 'weekday' not in ev_data:
                ev_data['weekday'] = change.get('weekday', '')
                ev_data['time'] = change.get('time', '')
                ev_data['pair_number'] = change.get('pair_number', 0)
                weekday_order = {"ПН": 1, "ВТ": 2, "СР": 3, "ЧТ": 4, "ПТ": 5, "СБ": 6, "ВС": 7}
                ev_data['order'] = weekday_order.get(ev_data['weekday'], 99)
                ev_data['type'] = change['change_type']

                if change['change_type'] in ('added', 'removed'):
                    ev_data['full_event'] = change.get('data', {})
                else:
                    ev_data['full_event'] = full_events.get(event_id, {})
                    ev_data['changes'] = ev_data.get('changes', [])
                    existing_fields = {ch['field'] for ch in ev_data['changes']}
                    for field_change in change.get('changes', []):
                        if field_change['field'] not in existing_fields:
                            ev_data['changes'].append(field_change)

    for user_id, events_dict in user_changes.items():
        user = next((u for u in users if u.telegram_id == user_id), None)
        if not user:
            continue

        groups_in_events = {ev['full_event'].get('group', '') for ev in events_dict.values()}
        is_group_subscription = (len(groups_in_events) == 1 and user.key in groups_in_events)

        if is_group_subscription:
            message = build_group_message(user.key, events_dict)
        else:
            message = build_teacher_message(user.key, events_dict)

        try:
            await bot.send_message(user_id, message, parse_mode='HTML', disable_web_page_preview=True)
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")