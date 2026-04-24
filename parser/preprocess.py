# [file name]: preprocess.py
import re
from typing import Union, List, Dict, Any, Tuple

# ---------- Константы для очистки ----------
CLEAN_REPLACEMENTS = {
    "\\": "", "\"": "", "“": "", "”": "", "«": "", "»": "",
    "—": "-", "–": "-", "−": "-", "‐": "-", "‑": "-",
    "`": "'", "´": "'",
    "„": "", "‚": "",
    "…": "...", "•": "*", "⋅": "*", "◦": "*"
}

# Предварительная компиляция регулярных выражений для производительности
_MULTIPLE_SPACES_RE = re.compile(r"\s+")
_MULTIPLE_DOTS_RE = re.compile(r"\.{2,}")
_MULTIPLE_DASHES_RE = re.compile(r"-{2,}")
_MULTIPLE_COMMAS_RE = re.compile(r",{2,}")
_CLEAN_PUNCTUATION_RE = re.compile(r"([!?])\1+")

# ---------- Основные функции очистки ----------
def clean(text: Union[str, None]) -> str:
    """Основная функция очистки строки от мусорных символов и лишних пробелов"""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    text = _replace_chars(text)
    text = _clean_with_regex(text)
    text = _normalize_spaces(text)
    return text.strip()

def _replace_chars(text: str) -> str:
    """Замена символов по словарю CLEAN_REPLACEMENTS"""
    trans_table = str.maketrans(CLEAN_REPLACEMENTS)
    return text.translate(trans_table)

def _clean_with_regex(text: str) -> str:
    """Применение регулярных выражений для схлопывания повторов"""
    text = text.replace("*", "•")
    text = _MULTIPLE_SPACES_RE.sub(" ", text)
    text = _MULTIPLE_DOTS_RE.sub(".", text)
    text = _MULTIPLE_DASHES_RE.sub("-", text)
    text = _MULTIPLE_COMMAS_RE.sub(",", text)
    text = _CLEAN_PUNCTUATION_RE.sub(r"\1", text)
    return text.strip()

def _normalize_spaces(text: str) -> str:
    """Нормализует пробелы вокруг знаков препинания"""
    text = re.sub(r"([,!?;])(\S)", r"\1 \2", text)
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    return text

import re

import re

def remove_academic_titles(text: str) -> str:
    if not text or not isinstance(text, str):
        return text

    titles = [
        # Составные (длинные) – должны обрабатываться первыми
        r'кандидат\s+(?:физ\.-мат\.|техн\.|экон\.|пед\.|филол\.|ист\.|биол\.|геогр\.|мед\.|воен\.)?\s*наук',
        r'доктор\s+(?:физ\.-мат\.|техн\.|экон\.|пед\.|филол\.|ист\.|биол\.|геогр\.|мед\.|воен\.)?\s*наук',
        r'старший\s+преподаватель',
        r'старший\s+научный\s+сотрудник',
        r'ст\.\s*науч\.?\s*сотр\.?',
        r'ст\.?\s*преподаватель',
        r'ст\.?\s*преп\.*',         # ст.преп, ст. преп, ст.преп. и т.п.
        r'профессор',
        r'ассистент',
        r'ассист\.*',               # ассист., ассист
        r'преподаватель',
        r'руководитель',
        r'ответственный',
        r'кандидат',
        r'доктор',
        r'учитель',
        r'доцент',
        r'чл\.-корр\.+',

        # Учёные степени с приставкой «наук»
        r'канд\.\s*(?:физ\.-мат\.|техн\.|экон\.|пед\.|филол\.|ист\.|биол\.|геогр\.|мед\.|воен\.)?\s*наук',
        r'д-р\.?\s*(?:физ\.-мат\.|техн\.|экон\.|пед\.|филол\.|ист\.|биол\.|геогр\.|мед\.|воен\.)?\s*наук',
        r'д\.\s*р\.?\s*(?:физ\.-мат\.|техн\.|экон\.|пед\.|филол\.|ист\.|биол\.|геогр\.|мед\.|воен\.)?\s*наук',
        r'[кд]\.[а-яё]+\.-?\s*[а-яё]+\.\s*н\.?',
        r'[кд]\.[а-яё]+\.\s*н\.?',

        # Одиночные сокращения
        r'проф\.+', r'доц\.+', r'преп\.+', r'асс\.+',
        r'отв\.+', r'рук\.+', r'каф\.+', r'акад\.+',
        r'канд\.+',                # канд.
        r'д-р\.*',                 # д-р, д-р.
        r'д\.\s*р\.+',             # д.р., д. р.
        r'д\.\s*р\.*',             # д.р, д р
        r'д-р\.?',                 # д-р, д-р.

        # Популярные к.т.н., д.ф.-м.н. и т.д.
        r'к\.\s*ф\.-?\s*м\.\s*н\.?',
        r'к\.\s*э\.\s*н\.?',
        r'д\.\s*т\.\s*н\.?',
        r'д\.\s*ф\.-?\s*м\.\s*н\.?',
        r'к\.\s*п\.\s*н\.?',
        r'д\.\s*п\.\s*н\.?',
        r'к\.\s*т\.\s*н\.?',
        r'к\.\s*ф\.\s*н\.?',
        r'к\.\s*б\.\s*н\.?',
        r'к\.\s*г\.\s*н\.?',
        r'к\.\s*и\.\s*н\.?',
        r'д\.\s*э\.\s*н\.?',
        r'д\.\s*ф\.\s*н\.?',
        r'д\.\s*б\.\s*н\.?',
        r'д\.\s*г\.\s*н\.?',
        r'д\.\s*и\.\s*н\.?',
    ]

    # Сортируем по убыванию длины паттерна, чтобы составные срабатывали раньше
    titles_sorted = sorted(titles, key=lambda x: len(x), reverse=True)

    for title in titles_sorted:
        # Удаляем, если после титула (с возможной запятой/пробелами) идёт заглавная буква или конец строки
        pattern = r'\b' + title + r'(?=\s*,?\s*[А-ЯA-Z]|\s*$)'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Убираем запятые и пробелы в начале строки, схлопываем двойные пробелы
    text = re.sub(r'^[,\s]+', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text

def normalize_room_number(room: str) -> str:
    """Убирает дефис между буквой и цифрами: А-231 -> А231."""
    room = re.sub(r'(?<=[А-Я])-(?=\d)', '', room, flags=re.IGNORECASE)
    return room.strip()


def normalize_rooms(line: str) -> List[str]:
    distant_pat = re.compile(r'дистанционно\s*[\\/]\s*СФЕРУМ', re.IGNORECASE)
    corpus_pat = re.compile(r'\b([IVX]+)\s+к\.\s*[\\/]?\s*', re.IGNORECASE)

    full_text = line
    result = []
    seen = set()

    # 1. "дистанционно СФЕРУМ"
    for m in distant_pat.finditer(full_text):
        val = "дистанционно СФЕРУМ"
        if val not in seen:
            seen.add(val)
            result.append(val)

    clean_text = distant_pat.sub(' ', full_text)
    clean_text = re.sub(r'\([^)]*\)', ' ', clean_text)
    clean_text = re.sub(r'\b\d{1,2}\.\d{2}(?:-\d{1,2}\.\d{2})?\b', ' ', clean_text)

    # 2. Обработка корпусов
    corpus_matches = list(corpus_pat.finditer(clean_text))
    for i, match in enumerate(corpus_matches):
        corpus_roman = match.group(1)
        corpus_norm = f"{corpus_roman} к."
        start = match.end()
        end = corpus_matches[i+1].start() if i+1 < len(corpus_matches) else len(clean_text)
        tail = clean_text[start:end]

        # Извлекаем все потенциальные токены аудиторий
        tokens = re.findall(r'[А-Яа-я\d-]+(?:\.\s*[А-Яа-я]+)?', tail, re.IGNORECASE)

        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # Особый случай: акт. зал
            if re.fullmatch(r'акт\.\s*зал', token, re.IGNORECASE):
                room = "акт. зал"
            else:
                # Удаляем ведущий числовой префикс с дефисом (05-А305 -> А305)
                room_clean = re.sub(r'^\d{1,2}-(?=[А-Я])', '', token, flags=re.IGNORECASE)
                room_clean = re.sub(r'\s+', ' ', room_clean).strip()

                # Валидация: число из ≥2 цифр или буква+цифры
                if re.fullmatch(r'\d{2,}', room_clean):
                    room = room_clean
                elif re.search(r'[А-Я]', room_clean, re.IGNORECASE) and re.search(r'\d', room_clean):
                    room = room_clean
                else:
                    continue

                # Убираем дефис между буквой и цифрой (А-406 -> А406)
                room = re.sub(r'(?<=[А-Я])-(?=\d)', '', room, flags=re.IGNORECASE)

            full_room = f"{corpus_norm} {room}"
            if full_room not in seen:
                seen.add(full_room)
                result.append(full_room)

    return result

def normalize_time(time_str: str) -> str:
    """
    Нормализует время из формата H-M, H:M, H.M, H M в HH:MM.
    Пример: "9-45" -> "09:45", "12-30" -> "12:30".
    """
    if not isinstance(time_str, str):
        return str(time_str)

    # Ищем два числа, разделённые нецифровым символом
    match = re.search(r'(\d{1,2})\D+(\d{1,2})', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        # Только если час и минута в допустимых пределах
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    # Если не подошло — возвращаем без изменений
    return time_str