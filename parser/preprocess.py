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
    """Нормализует пробелы вокруг знаков препинания, но не трогает даты вида число.число"""
    # Защищаем даты вида ДД.ММ или ДД.ММ.ГГГГ от разбиения
    date_pattern = r'\d{1,2}\.\d{2}(?:\.\d{4})?'
    text = re.sub(date_pattern, lambda m: m.group(0).replace('.', '\x00'), text)

    # Добавляем пробел после знака, если его нет
    text = re.sub(r'([,!?;])(\S)', r'\1 \2', text)
    # Убираем лишний пробел перед знаком
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    # Добавляем пробел после точки, если за ней не пробел и не цифра (чтобы не разбивать даты)
    text = re.sub(r'\.([А-Яа-яA-Za-z])', r'. \1', text)

    # Восстанавливаем даты
    text = text.replace('\x00', '.')
    return text

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

def english_to_russian_lookalike(text: str) -> str:
    """
    Заменяет одиночные латинские буквы на похожие русские,
    но не трогает целые слова (последовательности из двух и более латинских букв).
    """
    mapping = {
        # Заглавные
        'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
        'I': 'І', 'J': 'Ј', 'K': 'К', 'M': 'М', 'O': 'О',
        'P': 'Р', 'T': 'Т', 'W': 'Ш', 'X': 'Х', 'Y': 'У',
        # Строчные
        'a': 'а', 'b': 'ь', 'c': 'с', 'e': 'е', 'i': 'і',
        'j': 'ј', 'k': 'к', 'm': 'м', 'o': 'о', 'p': 'р',
        'w': 'ш', 'x': 'х', 'y': 'у',
    }

    # Паттерн находит любую последовательность латинских букв
    pattern = re.compile(r'[A-Za-z]+')

    def replacer(match: re.Match) -> str:
        word = match.group(0)
        if len(word) == 1:
            # Одиночная буква – заменяем, если есть аналог
            return mapping.get(word, word)
        else:
            # Слово или аббревиатура – оставляем как есть
            return word

    return pattern.sub(replacer, text)

def normalize_date_ranges(text: str, default_end_date: str = None) -> str:
    text = re.sub(r'(\d{1,2}\.\d{2}(?:\.\d{4})?)\s*[-–—]\s*(\d{1,2}\.\d{2}(?:\.\d{4})?)',
                  r'\1 - \2', text)
    # 1. Убираем точку в конце даты (06.02. -> 06.02)
    text = re.sub(r'(\d{1,2}\.\d{2}(?:\.\d{4})?)\.(?=\s|$|[,–—\-]|$)', r'\1', text)

    # 2. Нормализуем диапазоны "с дата1 - дата2" -> "дата1 - дата2"
    text = re.sub(
        r'\bс\s+(\d{1,2}\.\d{2}(?:\.\d{4})?)\s*[-–—]\s*(\d{1,2}\.\d{2}(?:\.\d{4})?)',
        r'\1 - \2',
        text,
        flags=re.IGNORECASE
    )

    # 3. Обрабатываем одиночные даты с "с" (без диапазона)
    if default_end_date:
        text = re.sub(
            r'\bс\s+(\d{1,2}\.\d{2}(?:\.\d{4})?)(?!\s*[-–—]\s*\d)',
            r'\1 - ' + default_end_date,
            text,
            flags=re.IGNORECASE
        )
    else:
        text = re.sub(r'\bс\s+(\d{1,2}\.\d{2}(?:\.\d{4})?)', r'\1', text, flags=re.IGNORECASE)

    # 4. Удаляем висячий дефис после даты (если нет второй даты)
    text = re.sub(r'(\d{1,2}\.\d{2}(?:\.\d{4})?)\s*[-–—]\s*(?![0-9])', r'\1', text)

    # 5. Принудительно вставляем дефис между двумя датами, разделёнными пробелом
    text = re.sub(r'(\d{1,2}\.\d{2}(?:\.\d{4})?)\s+(\d{1,2}\.\d{2}(?:\.\d{4})?)', r'\1 - \2', text)

    # 6. Чистим пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    # Гарантируем пробел после даты, если за ней идёт буква
    text = re.sub(r'(\d{1,2}\.\d{2})([А-Яа-я])', r'\1 \2', text)
    return text

def remove_invalid_dates(text: str) -> str:
    """Удаляет невалидные даты, но не трогает точки в валидных."""
    date_pattern_full = r'\b(\d{1,2})\.(\d{2})(?:\.(\d{4}))?\b'

    def is_valid_date(day_str: str, month_str: str, year_str: str = None) -> bool:
        try:
            day = int(day_str)
            month = int(month_str)
            if month < 1 or month > 12:
                return False
            if day < 1 or day > 31:
                return False
            if month in (4, 6, 9, 11) and day > 30:
                return False
            if month == 2 and day > 29:
                return False
            if year_str:
                year = int(year_str)
                if month == 2 and day == 29:
                    if not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
                        return False
            return True
        except ValueError:
            return False

    # 1. Обработка диапазонов дат
    def range_repl(m):
        date1_str = m.group(1)
        date2_str = m.group(2)
        parts1 = re.match(date_pattern_full, date1_str)
        parts2 = re.match(date_pattern_full, date2_str)
        if parts1 and parts2:
            d1, m1, y1 = parts1.groups()
            d2, m2, y2 = parts2.groups()
            if is_valid_date(d1, m1, y1) and is_valid_date(d2, m2, y2):
                return f"{date1_str} - {date2_str}"
        return ''

    text = re.sub(r'(\d{1,2}\.\d{2}(?:\.\d{4})?)\s*[-–—]\s*(\d{1,2}\.\d{2}(?:\.\d{4})?)', range_repl, text)

    # 2. Одиночные даты (удаляем только невалидные)
    def single_repl(m):
        date_str = m.group(1)
        parts = re.match(date_pattern_full, date_str)
        if parts:
            day, mon, year = parts.groups()
            if is_valid_date(day, mon, year):
                return date_str
        return ''

    text = re.sub(r'(?<!-)\b(\d{1,2}\.\d{2}(?:\.\d{4})?)\b(?!\s*-)', single_repl, text)

    # ----- ТВОЙ БЛОК (оставляем, но можно чуть упростить) -----
    # 3. Удаляем одиночные "с" или "c", которые остались после удаления дат
    text = re.sub(r'\b[сc]\s+', '', text, flags=re.IGNORECASE)

    # 4. Убираем лишние запятые
    text = re.sub(r',\s*,', ',', text)           # ", ," -> ","
    text = re.sub(r',\s*$', '', text)            # запятая в конце строки
    text = re.sub(r'^\s*,', '', text)            # запятая в начале
    text = re.sub(r'\s+', ' ', text)             # схлопываем пробелы
    text = re.sub(r'\s*,\s*', ', ', text)        # пробелы вокруг запятой

    # 5. Финальная чистка
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r' ,', ',', text)
    text = text.strip()
    return text

def extract_first_date(text: str) -> str:
    """
    Извлекает первую дату в формате ДД.ММ (или ДД.ММ.ГГГГ) из строки.
    Пример: "Экзаменационная сессия: 29.06 – 4.07.2026" -> "29.06"
    """
    match = re.search(r'\b(\d{1,2}\.\d{2})(?:\.\d{4})?\b', text)
    if match:
        return match.group(1)  # возвращаем только основную часть (ДД.ММ)
    return ""

import re

def remove_spaces_between_initials(text: str) -> str:
    """
    Удаляет пробел между инициалами: "И. О." -> "И.О."
    Оставляет без изменений даты, сокращения, числа.
    """
    # Защищаем даты (цифра.цифра или цифра.цифра.цифра) от изменений
    date_pattern = r'\b\d{1,2}\.\d{2}(?:\.\d{4})?\b'
    protected = {}

    def replacer(match):
        placeholder = f'__DATE_{len(protected)}__'
        protected[placeholder] = match.group(0)
        return placeholder

    text = re.sub(date_pattern, replacer, text)

    # Ищем шаблон: заглавная буква (кириллица или латиница), точка, пробелы, заглавная буква, точка
    # Превращаем в "Буква.Буква." без пробела
    text = re.sub(r'([A-ZА-ЯЁ])\.\s+([A-ZА-ЯЁ])\.', r'\1.\2.', text)

    # Восстанавливаем даты
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)

    return text


def normalize_subgroup(text: str) -> str:
    """
    Приводит различные написания подгрупп (п/г1, пг 2, п\\г 2, п/г 1 и т.п.)
    к единому виду "п/г N", где N — номер группы.
    """
    # Шаблон: "п", затем возможные разделители (пробелы, слеш, обратный слеш),
    # затем "г", затем снова возможные разделители, затем одна или более цифр.
    pattern = r'\bп\s*[\/\\]?\s*г\s*(\d+)\b'
    return re.sub(pattern, r'п/г \1', text)