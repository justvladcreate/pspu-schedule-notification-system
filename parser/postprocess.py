# [file name]: postprocess.py
import json
from typing import Dict, List, Any, Tuple

def load_snapshot(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def compare_snapshots(new_path: str, old_path: str) -> List[Dict[str, Any]]:
    """
    Сравнивает два снимка расписания и возвращает список изменений.
    Каждое изменение – словарь с типом ('added', 'removed', 'changed')
    и всей необходимой информацией для записи в БД и уведомлений.
    """
    old_data = load_snapshot(old_path)["events"]
    new_data = load_snapshot(new_path)["events"]

    old_by_id = {ev["event_id"]: ev for ev in old_data}
    new_by_id = {ev["event_id"]: ev for ev in new_data}

    changes = []

    # Обрабатываем добавленные и изменённые
    for event_id, new_ev in new_by_id.items():
        if event_id not in old_by_id:
            changes.append({
                "change_type": "added",
                "event_id": event_id,
                "group": new_ev["group"],
                "weekday": new_ev["weekday"],
                "pair_number": new_ev["pair_number"],
                "time": new_ev["time"],
                "data": new_ev
            })
        else:
            old_ev = old_by_id[event_id]
            changed_fields = _get_changed_fields(old_ev, new_ev)
            if changed_fields:
                changes.append({
                    "change_type": "changed",
                    "event_id": event_id,
                    "group": new_ev["group"],
                    "weekday": new_ev["weekday"],
                    "pair_number": new_ev["pair_number"],
                    "time": new_ev["time"],
                    "changes": changed_fields
                })

    # Обрабатываем удалённые
    for event_id, old_ev in old_by_id.items():
        if event_id not in new_by_id:
            changes.append({
                "change_type": "removed",
                "event_id": event_id,
                "group": old_ev["group"],
                "weekday": old_ev["weekday"],
                "pair_number": old_ev["pair_number"],
                "time": old_ev["time"],
                "data": old_ev
            })

    return changes

def _get_changed_fields(old: Dict, new: Dict) -> List[Dict[str, str]]:
    """Сравнивает атрибуты событий (кроме event_id, group, weekday, time, pair_number)."""
    fields_to_compare = [
        "discipline", "teachers", "dates", "rooms", "type", "subgroup", "comment"
    ]
    changed = []
    for field in fields_to_compare:
        old_val = _normalize_for_comparison(old.get(field))
        new_val = _normalize_for_comparison(new.get(field))
        if old_val != new_val:
            changed.append({
                "field": field,
                "old_value": old_val,
                "new_value": new_val
            })
    return changed

def _normalize_for_comparison(value: Any) -> str:
    """Приводит значение к строке для сравнения; списки сортируем."""
    if isinstance(value, list):
        return ", ".join(sorted([str(v) for v in value]))
    elif value is None:
        return ""
    return str(value)


import re

def remove_academic_titles(text: str) -> str:
    """
    Удаляет академические титулы и учёные степени из строки, содержащей
    имя с возможными титулами (например, "доц. Зорин А.А.").
    Возвращает очищенное имя или пустую строку, если остался только титул.
    """
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
        r'ст\.?\s*преп\.*',
        r'профессор',
        r'ассистент',
        r'ассист\.*',
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
        r'канд\.+',
        r'д-р\.*',
        r'д\.\s*р\.+',
        r'д\.\s*р\.*',
        r'д-р\.?',

        # Добавлены отсутствовавшие варианты: рук-ль, рк-ль
        r'рук-ль',          # рук-ль (например, "рук-ль доц. Липкина Н.Г.")
        r'рк-ль',           # опечатка/сокращение от "руководитель"
        r'рук\.\s*-?\s*ль', # на случай "рук.ль", "рук.-ль" и т.п.

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

    # Сначала обрабатываем самые длинные составные титулы
    titles_sorted = sorted(titles, key=lambda x: len(x), reverse=True)

    for title in titles_sorted:
        # Удаляем титул, если за ним (возможно с запятой) идёт заглавная буква или конец строки
        pattern = r'\b' + title + r'(?=\s*,?\s*[А-ЯA-Z]|\s*$)'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Чистим остатки: ведущие запятые/пробелы и сдвоенные пробелы
    text = re.sub(r'^[,\s]+', '', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text