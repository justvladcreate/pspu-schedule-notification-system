# [file name]: preprocess.py
import re
from typing import Union
class DataParser:
    def __init__(self):
        self.clean_replacements = {
            "\\": "", "\"": "", "“": "", "”": "", "«": "", "»": "",
            "—": "-", "–": "-", "−": "-", "‐": "-", "‑": "-",
            "`": "'", "´": "'",
            "„": "", "‚": "",
            "…": "...", "•": "*", "⋅": "*", "◦": "*"
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
        text = text.replace("*", "•")
        text = self.multiple_spaces_re.sub(" ", text)
        text = self.multiple_dots_re.sub(".", text)
        text = self.multiple_dashes_re.sub("-", text)
        text = self.multiple_commas_re.sub(",", text)
        text = self.clean_punctuation_re.sub(r"\1", text)
        text = text.strip()
        
        return text
        
    def extract_all_subjects(self,text: str) -> str:
        text = re.sub(r'\d{1,2}\.\d{1,2}', ' ', text)
        text = re.sub(r'с?\s*\d{1,2}\.\d{1,2}\s*-\s*\d{1,2}\.\d{1,2}', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d{1,2}\.\d{1,2}\s*,\s*)+\d{1,2}\.\d{1,2}', ' ', text)
        text = re.sub(r'\([^)]*\)', ' ', text)
        text = re.sub(r'п\\?г\s*\d', ' ', text)
        text = re.sub(r'ст\.', ' ', text)
        text = re.sub(r'(лек|лаб|прак)\.?', ' ', text, flags=re.IGNORECASE)

        parts = re.split(r'[,;\n]|с\s', text)
        cleaned = []
        for p in parts:
            p = p.strip()
            p = re.sub(r'\s+', ' ', p)
            if len(p) < 4:
                continue
            cleaned.append(p)

        unique = []
        for c in cleaned:
            if c not in unique:
                unique.append(c)

        return "; ".join(unique)
    
    def _normalize_spaces(self, text: str) -> str:
        text = re.sub(r"([,!?;])([^\s])", r"\1 \2", text)
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)
        
        return text
    
    def parse_row(self, raw_time, raw_subject, raw_teacher, raw_room, inline = True):
        time = self.clean(raw_time).replace("-", ":")
        subject = self.clean(raw_subject)
        teacher = self.clean(raw_teacher)
        room = self.clean(raw_room)

        if inline:
            result = f"{time} | {subject} | {teacher} | {room}"
            return result
        else:
            return time, subject, teacher, room
    
    def parse_info(self, info, inline = True):
        parsed_rows = []

        new_times = []
        new_subjects = []
        new_teachers = []
        new_rooms = []

        # Обрабатываем новую структуру данных
        times = info.get("times", [])
        subjects = info.get("subjects", [])
        teachers = info.get("teachers", [])
        rooms = info.get("rooms", [])
        
        if inline:
            for time_item, subject_item, teacher_item, room_item in zip(times, subjects, teachers, rooms):
                parsed_rows.append(self.parse_row(
                    time_item["value"], 
                    subject_item["value"], 
                    teacher_item["value"], 
                    room_item["value"], 
                    inline
                ))
            return parsed_rows
        else:
            for time_item, subject_item, teacher_item, room_item in zip(times, subjects, teachers, rooms):
                new_time, new_subject, new_teacher, new_room = self.parse_row(
                    time_item["value"], 
                    subject_item["value"], 
                    teacher_item["value"], 
                    room_item["value"], 
                    inline
                )
                new_times.append({"cell": time_item["cell"], "value": new_time})
                new_subjects.append({"cell": subject_item["cell"], "value": new_subject})
                new_teachers.append({"cell": teacher_item["cell"], "value": new_teacher})
                new_rooms.append({"cell": room_item["cell"], "value": new_room})
                
            return new_times, new_subjects, new_teachers, new_rooms
    
    def parse(self, groups_info):
        for group_name in groups_info:
            info = groups_info[group_name]
            if info is None:
                continue

            parsed_subject_info = self.parse_info(info, inline=True)
            new_times, new_subjects, new_teachers, new_rooms = self.parse_info(info, inline=False)
            
            if not parsed_subject_info: 
                continue
            
            groups_info[group_name]['times'] = new_times
            groups_info[group_name]['subjects'] = new_subjects
            groups_info[group_name]['teachers'] = new_teachers
            groups_info[group_name]['rooms'] = new_rooms

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