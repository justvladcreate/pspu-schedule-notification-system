import json
import re
from typing import Dict, List, Optional, Any
from datetime import time

# Карта соответствия времени начала пары номеру пары
PAIR_INTERVALS = [
    (time(8, 0),  time(9, 45)),  # 1-я пара
    (time(9, 45), time(11, 30)), # 2-я пара
    (time(11, 30), time(13, 30)),# 3-я пара
    (time(13, 30), time(15, 15)),# 4-я пара
    (time(15, 15), time(17, 0)), # 5-я пара
    (time(17, 0),  time(18, 45)),# 6-я пара
    (time(18, 45), time(20, 15)) # 7-я пара
]


def parse_event_string(event_str: str) -> Dict[str, str]:
    """Разбирает строку события на словарь параметров."""
    params = {}
    # Разделяем по '; ' (точка с запятой и пробел)
    parts = [p.strip() for p in event_str.split("; ")]
    for part in parts:
        if ": " in part:
            key, value = part.split(": ", 1)
            params[key] = value
        elif part.endswith(":"):
            # Пустое значение (например, "type: ;" превращается в "type:")
            key = part[:-1]
            params[key] = ""
    return params

def get_pair_number(time_str: str) -> Optional[int]:
    """Возвращает номер пары (1-7) для времени в формате HH:MM или None."""
    try:
        h, m = map(int, time_str.strip().split(':'))
        t = time(h, m)
        # Проверяем все интервалы
        for i, (start, end) in enumerate(PAIR_INTERVALS, start=1):
            if start <= t < end:
                return i
        # Особая проверка на точное время окончания 7-й пары (20:15)
        if t == time(20, 15):
            return 7
    except (ValueError, AttributeError):
        pass
    return None

def extract_weekday_and_time(time_str: str) -> tuple[str, str]:
    """Извлекает день недели и время из строки вида 'ПН 09:45'."""
    parts = time_str.split()
    weekday = parts[0]  # "ПН", "ВТ" и т.д.
    time = parts[1] if len(parts) > 1 else ""
    return weekday, time

def normalize_teachers(teacher_str: str) -> List[str]:
    """Превращает строку преподавателей в список."""
    if not teacher_str:
        return []
    teachers = [t.strip() for t in teacher_str.split(",") if t.strip()]
    return teachers

def transform_schedule(raw_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
    all_events = []

    for group, group_data in raw_data.items():
        event_strings = group_data.get("events", [])
        position_counter: Dict[tuple, int] = {}

        for event_str in event_strings:
            params = parse_event_string(event_str)

            time_raw = params.get("time", "")
            if not time_raw:
                continue
            weekday, time_val = extract_weekday_and_time(time_raw)
            pair_number = get_pair_number(time_val)  # <-- используем новую функцию
            if pair_number is None:
                continue

            dates = params.get("dates", "")
            discipline = params.get("discipline", "")
            type_raw = params.get("type", "")
            subgroup_raw = params.get("subgroup", "")
            teachers_raw = params.get("teachers", "")
            rooms_raw = params.get("rooms", "")
            comment = params.get("comment", "")

            key = (weekday, pair_number)
            position_counter[key] = position_counter.get(key, 0) + 1
            position = position_counter[key]

            event_id = f"{group}_{weekday}_{pair_number}_{position}"

            teachers = normalize_teachers(teachers_raw)
            event = {
                "event_id": event_id,
                "group": group,
                "weekday": weekday,
                "time": time_val,           # исходное время, например "15:30"
                "pair_number": pair_number, # номер пары 4
                "position": position,
                "discipline": discipline,
                "teachers": teachers,
                "dates": dates,
                "rooms": rooms_raw,
                "type": type_raw,
                "subgroup": subgroup_raw,
                "comment": comment
            }
            all_events.append(event)

    return {"events": all_events}


