# [file name]: date_parser.py
"""
Парсинг ячеек расписания с датами.

Форматы:
  - "с 3.02 - 10.03 Предмет1, с 17.03 - Предмет2"
  - "11.02 Предмет" (без "с" — значит "начиная с 11.02")
  - "с 18.02 - 3.03, с 17.03 - 31.03, с 14.04 - Предмет" (несколько диапазонов, один предмет)
  - "16.02 Предмет1 30.03 Предмет2" (два предмета с датами)
  - "IV к. А305 25.03 - дистанционно СФЕРУМ" (даты в кабинетах)
"""

import re
from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Учебный год
_today = date.today()
if _today.month >= 8:
    ACADEMIC_YEAR_START = _today.year
else:
    ACADEMIC_YEAR_START = _today.year - 1

# Длительность пары
LESSON_DURATION = timedelta(hours=1, minutes=30)

# Стандартное расписание звонков
LESSON_TIMES = {
    "08:00": "09:30",
    "8:00": "09:30",
    "09:45": "11:15",
    "9:45": "11:15",
    "11:30": "13:00",
    "13:30": "15:00",
    "15:15": "16:45",
    "15:30": "17:00",
    "17:00": "18:30",
    "18:45": "20:15",
}


def get_lesson_end_time(start_time_str):
    """Вычисляет время окончания пары по времени начала"""
    # Убираем день недели
    time_only = start_time_str
    for day in ("ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ",
                "ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"):
        time_only = time_only.replace(day, "").strip()

    # Нормализуем формат
    time_only = time_only.replace(":", ":").replace("-", ":").strip()

    # Ищем в таблице
    if time_only in LESSON_TIMES:
        return LESSON_TIMES[time_only]

    # Вычисляем вручную
    try:
        # Пробуем разные форматы
        for fmt in ("%H:%M", "%H.%M", "%H %M"):
            try:
                t = datetime.strptime(time_only, fmt)
                end = t + LESSON_DURATION
                return end.strftime("%H:%M")
            except ValueError:
                continue
    except Exception:
        pass

    return None


def parse_date(day_str, month_str):
    """Парсит дату вида '3', '02' → date(year, 2, 3)"""
    try:
        day = int(day_str)
        month = int(month_str)
        if month >= 8:
            year = ACADEMIC_YEAR_START
        else:
            year = ACADEMIC_YEAR_START + 1
        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def is_date_like(text):
    """Проверяет, похоже ли начало текста на дату DD.MM"""
    return bool(re.match(r'^\d{1,2}\.\d{2}\b', text.strip()))


def split_by_dates(text):
    """
    Разбивает текст ячейки на сегменты по датам.

    Возвращает список:
    [{"date_from": date|None, "date_to": date|None, "text": "..."}, ...]
    """
    if not text or not text.strip():
        return [{"date_from": None, "date_to": None, "text": text or ""}]

    # Универсальный паттерн для всех форматов дат
    # Группа 1-4: диапазон DD.MM - DD.MM (с опциональным "с/c")
    # Группа 5-6: "с DD.MM" (только начало)
    # Группа 7-8: standalone DD.MM в начале или после пробела
    date_pattern = re.compile(
        r'(?:[сcСC]\s*)?(\d{1,2})\.(\d{2})\s*[-–—]\s*(\d{1,2})\.(\d{2})'  # диапазон
        r'|'
        r'[сcСC]\s+(\d{1,2})\.(\d{2})'  # "с DD.MM"
        r'|'
        r'(?:^|(?<=\s)|(?<=,\s))(\d{1,2})\.(\d{2})(?=\s+[-–—]|\s+[А-ЯЁA-Z]|\s*$)'  # standalone DD.MM
    )

    matches = list(date_pattern.finditer(text))

    if not matches:
        return [{"date_from": None, "date_to": None, "text": text.strip()}]

    # Объединяем перечисленные диапазоны "с 18.02 - 3.03, с 17.03 - 31.03, с 14.04 - Предмет"
    # Если несколько диапазонов подряд без текста между ними — это один предмет
    segments = []
    i = 0

    while i < len(matches):
        m = matches[i]
        date_from, date_to = _extract_dates(m)

        # Проверяем: если дальше идут даты без текста (или только запятая) — объединяем
        combined_ranges = [(date_from, date_to)]
        last_match_end = m.end()

        j = i + 1
        while j < len(matches):
            between = text[last_match_end:matches[j].start()].strip()
            # Между диапазонами только запятая/пробел/пусто — это список дат одного предмета
            if between in ("", ",", ", "):
                next_from, next_to = _extract_dates(matches[j])
                combined_ranges.append((next_from, next_to))
                last_match_end = matches[j].end()
                j += 1
            else:
                break

        # Текст после последнего диапазона в цепочке
        text_start = last_match_end
        if j < len(matches):
            text_end = matches[j].start()
        else:
            text_end = len(text)

        segment_text = text[text_start:text_end].strip()
        segment_text = re.sub(r'^[\s\-–—,]+', '', segment_text).strip()
        segment_text = segment_text.rstrip(',').strip()

        # Для объединённых диапазонов: берём самую раннюю from и самую позднюю to
        # Но если это несколько отдельных периодов, они все активны
        all_froms = [r[0] for r in combined_ranges if r[0]]
        all_tos = [r[1] for r in combined_ranges if r[1]]

        segments.append({
            "date_from": min(all_froms) if all_froms else None,
            "date_to": max(all_tos) if all_tos else None,
            "date_ranges": combined_ranges,  # все отдельные диапазоны
            "text": segment_text,
        })

        i = j

    # Текст перед первой датой
    if matches and matches[0].start() > 0:
        prefix_text = text[:matches[0].start()].strip().rstrip(',').strip()
        # Фильтруем мусор (одиночные "с", "c", пробелы)
        if prefix_text and len(prefix_text) > 2:
            segments.insert(0, {
                "date_from": None,
                "date_to": None,
                "date_ranges": [],
                "text": prefix_text,
            })

    return segments


def _extract_dates(match):
    """Извлекает даты из regex match"""
    if match.group(1):  # диапазон DD.MM - DD.MM
        return parse_date(match.group(1), match.group(2)), parse_date(match.group(3), match.group(4))
    elif match.group(5):  # "с DD.MM"
        return parse_date(match.group(5), match.group(6)), None
    elif match.group(7):  # standalone DD.MM
        return parse_date(match.group(7), match.group(8)), None
    return None, None


def is_segment_active(segment, check_date=None):
    """Проверяет, активен ли сегмент на заданную дату"""
    if check_date is None:
        check_date = date.today()

    # Если есть конкретные диапазоны — проверяем каждый
    date_ranges = segment.get("date_ranges", [])
    if date_ranges:
        for dfrom, dto in date_ranges:
            if dfrom and dto:
                if dfrom <= check_date <= dto:
                    return True
            elif dfrom and not dto:
                if check_date >= dfrom:
                    return True
            elif not dfrom and not dto:
                return True
        return False

    # Фолбэк на простые поля
    date_from = segment.get("date_from")
    date_to = segment.get("date_to")

    if date_from is None and date_to is None:
        return True

    if date_from and date_to:
        return date_from <= check_date <= date_to

    if date_from and not date_to:
        return check_date >= date_from

    return True


def get_active_subject(subject_text, check_date=None):
    """Из текста ячейки возвращает активный предмет на текущую дату"""
    segments = split_by_dates(subject_text)
    active = [s for s in segments if is_segment_active(s, check_date)]

    if active:
        texts = [s["text"] for s in active if s["text"]]
        if texts:
            return "; ".join(texts)

    # Фолбэк
    return subject_text


def get_active_room(room_text, check_date=None):
    """Из текста ячейки с кабинетами возвращает активный кабинет"""
    if not room_text or not room_text.strip():
        return room_text

    segments = split_by_dates(room_text)
    active = [s for s in segments if is_segment_active(s, check_date)]

    if active:
        texts = [s["text"] for s in active if s["text"]]
        if texts:
            return "; ".join(texts)

    return room_text


def get_all_segments(subject_text, room_text):
    """Разбивает предмет и кабинет на сегменты с датами"""
    subject_segments = split_by_dates(subject_text)
    room_segments = split_by_dates(room_text)

    results = []

    if len(subject_segments) == len(room_segments):
        for subj, room in zip(subject_segments, room_segments):
            results.append({
                "subject": subj["text"],
                "room": room["text"],
                "date_from": subj["date_from"] or room["date_from"],
                "date_to": subj["date_to"] or room["date_to"],
            })
    else:
        for subj in subject_segments:
            active_room = get_active_room(room_text, subj.get("date_from"))
            results.append({
                "subject": subj["text"],
                "room": active_room,
                "date_from": subj["date_from"],
                "date_to": subj["date_to"],
            })

    return results
