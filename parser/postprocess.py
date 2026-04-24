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