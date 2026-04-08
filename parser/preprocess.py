# [file name]: preprocess.py
import re
from typing import Union
from .date_parser import get_active_subject, get_active_room


class DataParser:
    def __init__(self):
        self.clean_replacements = {
            "\\": "", "\"": "", "\u201c": "", "\u201d": "", "\u00ab": "", "\u00bb": "",
            "\u2014": "-", "\u2013": "-", "\u2212": "-", "\u2010": "-", "\u2011": "-",
            "`": "'", "\u00b4": "'",
            "\u201e": "", "\u201a": "",
            "\u2026": "...", "\u2022": "*", "\u22c5": "*", "\u25e6": "*"
        }
        self.multiple_spaces_re = re.compile(r"\s+")
        self.multiple_dots_re = re.compile(r"\.{2,}")
        self.multiple_dashes_re = re.compile(r"-{2,}")
        self.multiple_commas_re = re.compile(r",{2,}")
        self.clean_punctuation_re = re.compile(r"([!?])\1+")

    def clean(self, text: Union[str, None]) -> str:
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        text = self._replace_chars(text)
        text = self._clean_with_regex(text)
        text = self._normalize_spaces(text)
        return text.strip()

    def _replace_chars(self, text: str) -> str:
        if not hasattr(self, '_translation_table'):
            self._translation_table = str.maketrans(self.clean_replacements)
        return text.translate(self._translation_table)

    def _clean_with_regex(self, text: str) -> str:
        text = text.replace("*", "\u2022")
        text = self.multiple_spaces_re.sub(" ", text)
        text = self.multiple_dots_re.sub(".", text)
        text = self.multiple_dashes_re.sub("-", text)
        text = self.multiple_commas_re.sub(",", text)
        text = self.clean_punctuation_re.sub(r"\1", text)
        return text.strip()

    def _normalize_spaces(self, text: str) -> str:
        text = re.sub(r"([,!?;])([^\s])", r"\1 \2", text)
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)
        return text

    def parse_row(self, raw_time, raw_subject, raw_teacher, raw_room, is_grey=False, is_event=False, inline=True):
        time = self.clean(raw_time).replace("-", ":")
        subject = self.clean(raw_subject)
        teacher = self.clean(raw_teacher)
        room = self.clean(raw_room)

        # Для активного предмета на текущую дату
        active_subject = get_active_subject(subject)
        active_room = get_active_room(room)

        if inline:
            result = f"{time} | {active_subject} | {teacher} | {active_room}"
            return result
        else:
            return time, subject, teacher, room, active_subject, active_room

    def parse_info(self, info, inline=True):
        parsed_rows = []
        new_times = []
        new_subjects = []
        new_teachers = []
        new_rooms = []
        new_active_subjects = []
        new_active_rooms = []

        times = info.get("times", [])
        subjects = info.get("subjects", [])
        teachers = info.get("teachers", [])
        rooms = info.get("rooms", [])
        grey_flags = info.get("grey_flags", [False] * len(times))
        event_flags = info.get("event_flags", [False] * len(times))

        if inline:
            for time_item, subject_item, teacher_item, room_item, is_grey, is_event in zip(
                times, subjects, teachers, rooms, grey_flags, event_flags
            ):
                parsed_rows.append(self.parse_row(
                    time_item["value"],
                    subject_item["value"],
                    teacher_item["value"],
                    room_item["value"],
                    is_grey,
                    is_event,
                    inline
                ))
            return parsed_rows
        else:
            for time_item, subject_item, teacher_item, room_item, is_grey, is_event in zip(
                times, subjects, teachers, rooms, grey_flags, event_flags
            ):
                time, subject, teacher, room, active_subject, active_room = self.parse_row(
                    time_item["value"],
                    subject_item["value"],
                    teacher_item["value"],
                    room_item["value"],
                    is_grey,
                    is_event,
                    inline
                )
                new_times.append({"cell": time_item["cell"], "value": time})
                new_subjects.append({"cell": subject_item["cell"], "value": subject})
                new_teachers.append({"cell": teacher_item["cell"], "value": teacher})
                new_rooms.append({"cell": room_item["cell"], "value": room})
                new_active_subjects.append({"cell": subject_item["cell"], "value": active_subject})
                new_active_rooms.append({"cell": room_item["cell"], "value": active_room})

            return new_times, new_subjects, new_teachers, new_rooms, new_active_subjects, new_active_rooms

    def parse(self, groups_info):
        for group_name in groups_info:
            info = groups_info[group_name]
            if info is None:
                continue

            parsed_subject_info = self.parse_info(info, inline=True)
            result = self.parse_info(info, inline=False)
            new_times, new_subjects, new_teachers, new_rooms, new_active_subjects, new_active_rooms = result

            if not parsed_subject_info:
                continue

            groups_info[group_name]['times'] = new_times
            groups_info[group_name]['subjects'] = new_subjects
            groups_info[group_name]['teachers'] = new_teachers
            groups_info[group_name]['rooms'] = new_rooms
            groups_info[group_name]['active_subjects'] = new_active_subjects
            groups_info[group_name]['active_rooms'] = new_active_rooms

        return groups_info

    def parse_response(self, text):
        parts = [part.strip() for part in text.split('|')]
        while len(parts) < 7:
            parts.append('')
        time = parts[0] if len(parts) > 0 else ''
        dates = parts[1] if len(parts) > 1 else ''
        subject = parts[2] if len(parts) > 2 else ''
        lesson_type = parts[3] if len(parts) > 3 else ''
        subgroup = parts[4] if len(parts) > 4 else ''
        teacher = parts[5] if len(parts) > 5 else ''
        classroom = parts[6] if len(parts) > 6 else ''
        return time, dates, subject, lesson_type, subgroup, teacher, classroom
