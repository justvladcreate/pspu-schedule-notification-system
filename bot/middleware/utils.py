import json
import os
from pathlib import Path
from typing import List, Set, Optional

from .database import SessionLocal, User, init_db

init_db()

# Путь к файлу с расписанием (результат парсера)
DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "latest" / "groups_info_parsed.json"

# ----- кэш преподавателей и групп -----
class DataCache:
    def __init__(self, json_path: Path):
        self.json_path = json_path
        self._teachers: List[str] = []
        self._groups: List[str] = []
        self._last_mtime: float = 0

    def _load(self):
        if not self.json_path.exists():
            self._teachers, self._groups = [], []
            return
        try:
            current_mtime = self.json_path.stat().st_mtime
            if current_mtime == self._last_mtime:
                return
            self._last_mtime = current_mtime
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._teachers, self._groups = [], []
            return

        teachers_set: Set[str] = set()
        groups_set: Set[str] = set()
        for event in data.get('events', []):
            group = event.get('group', '').strip()
            if group:
                groups_set.add(group)
            for teacher in event.get('teachers', []):
                teacher = teacher.strip()
                if teacher:
                    teachers_set.add(teacher)
        self._teachers = sorted(teachers_set)
        self._groups = sorted(groups_set)

    def get_teachers(self) -> List[str]:
        self._load()
        return self._teachers

    def get_groups(self) -> List[str]:
        self._load()
        return self._groups

    # для обратной совместимости (в keyboard_handlers использовалась get_all_teachers)
    def get_all_teachers(self) -> Set[str]:
        return set(self.get_teachers())

    def get_all_groups(self) -> List[str]:
        return self.get_groups()


# глобальный объект кэша
cache = DataCache(DATA_PATH)

# ----- вспомогательные функции -----
def get_available_letters(teachers_list):
    """Буквы, для которых есть преподаватели"""
    letters_set = set()
    for t in teachers_list:
        if t.strip():
            parts = t.split()
            if parts:
                first_letter = parts[0][0].upper()
                letters_set.add(first_letter)
    return sorted(letters_set)

def normalize_key(raw: str) -> str:
    """Приводит ввод к единому формату (Фамилия И.О. или номер группы)"""
    key = raw.strip().replace('ё', 'е').replace('Ё', 'Е')
    has_digits = any(ch.isdigit() for ch in key)
    if has_digits:
        return key[:30]

    # ФИО
    parts = [p for p in key.split() if p]
    if not parts:
        return key[:30]
    if len(parts) == 1:
        return parts[0].title()[:30]

    surname = parts[0].title()
    initials = []
    for part in parts[1:]:
        clean = part.strip('.')
        if clean:
            initials.append(clean[0].upper())
    formatted = surname
    if initials:
        formatted += ' ' + '.'.join(initials) + '.'
    return formatted[:30]

def get_user_subscription(tg_id: int) -> Optional[str]:
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(telegram_id=tg_id).first()
        return user.key if user else None
    finally:
        session.close()