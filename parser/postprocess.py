# [file name]: postprocess.py
import re
from difflib import SequenceMatcher
from collections import defaultdict

class DataManager:
    def __init__(self):
        pass

    @staticmethod
    def normalize_room(text: str) -> str:
        if text is None:
            return ""
        cleaned = text.replace("\n", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = cleaned.replace("\\", "")
        return cleaned

    @staticmethod
    def highlight_changes(old: str, new: str) -> str:
        sm = SequenceMatcher(None, old, new)
        result = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                result.append(new[j1:j2])
            elif tag in ("replace", "insert"):
                result.append("<u><b>" + new[j1:j2] + "</b></u>")
            elif tag == "delete":
                pass
        return "".join(result)

    def prepare_mapping(self, items):
        mapping = {}
        for item in items:
            cell = item["cell"]
            value = self.normalize_room(item["value"])
            if value:
                mapping[cell] = value
        return mapping
    
    def escape_html(self, text: str) -> str:
        if not text:
            return ""
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace('"', "&quot;"))

    def create_hyperlink(self, cell_address, sheet_id=0):
        file_id = "1_fsm-OxH9E9LgHnLC0iju5OlaHIv0agmM87GLvRKIAg"
        if cell_address:
            url = f"https://docs.google.com/spreadsheets/d/{file_id}/edit#gid={sheet_id}&range={cell_address}"
        else:
            url = f"https://docs.google.com/spreadsheets/d/{file_id}/edit#gid={sheet_id}"
        
        return f'<a href="{url}">[См. табл.]</a>'

    def similar_strings(self, str1, str2, threshold=0.8):
        """Проверяет схожесть строк"""
        if not str1 and not str2:
            return True
        if not str1 or not str2:
            return False
            
        s1 = str(str1).lower().strip()
        s2 = str(str2).lower().strip()
        
        if s1 == s2:
            return True
        
        if s1 in s2 or s2 in s1:
            return True
        
        similarity = SequenceMatcher(None, s1, s2).ratio()
        return similarity >= threshold

    def get_record_key(self, time, subject, teacher):
        """Создает ключ для записи на основе содержания"""
        # Нормализуем день недели в начале времени
        time_str = str(time).strip()
        
        # Извлекаем день недели если есть
        day_of_week = ""
        for day in ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]:
            if time_str.startswith(day):
                day_of_week = day
                time_str = time_str.replace(day, "").strip()
                break
        
        # Нормализуем время (убираем лишние пробелы)
        time_str = re.sub(r'\s+', ' ', time_str).strip()
        
        # Нормализуем преподавателя (группируем нескольких преподавателей как одну строку)
        teacher_norm = self.normalize_teacher_string(teacher)
        
        # Возвращаем ключ без учета аудитории
        key = f"{day_of_week}|{time_str}|{subject}|{teacher_norm}"
        return key

    def normalize_teacher_string(self, teacher_str):
        """Нормализует строку с преподавателями, группируя нескольких вместе"""
        if not teacher_str:
            return ""
        
        # Разделяем преподавателей
        teachers = self.split_teachers(teacher_str)
        
        # Сортируем для единообразия и объединяем обратно
        sorted_teachers = sorted(teachers)
        return ", ".join(sorted_teachers).lower()

    def prepare_records_by_key(self, group_data):
        """Подготавливает записи с ключами на основе содержания"""
        records_by_key = {}
        
        for time_item, subject_item, teacher_item, room_item in zip(
            group_data["times"], group_data["subjects"], 
            group_data["teachers"], group_data["rooms"]
        ):
            time_val = time_item["value"]
            subject_val = subject_item["value"]
            teacher_val = teacher_item["value"]
            
            # Создаем ключ на основе содержания
            record_key = self.get_record_key(time_val, subject_val, teacher_val)
            
            records_by_key[record_key] = {
                "cell": room_item["cell"],
                "room": room_item["value"],
                "time": time_val,
                "subject": subject_val,
                "teacher": teacher_val,
                "time_cell": time_item["cell"],
                "subject_cell": subject_item["cell"],
                "teacher_cell": teacher_item["cell"]
            }
        
        return records_by_key

    def compare(self, groups_info_old, groups_info):
        old_map = groups_info_old
        new_map = groups_info

        all_changes = {
        "general": [],
        "teachers": defaultdict(lambda: defaultdict(list)),
        "groups": defaultdict(list)
        }

        for group_name, new_data in new_map.items():
            old_data = old_map.get(group_name)

            if old_data is None:
                link = self.create_hyperlink(sheet_id=new_data['sheet_id'])
                escaped_group_name = self.escape_html(group_name)
                change_message = f"➕ Появилась новая группа: {escaped_group_name} {link}"
                
                all_changes["general"].append(change_message)
                continue

            compared_data = self.compare_data(old_data, new_data, group_name)
            
            # Добавляем изменения без разделения преподавателей
            for teacher_key, changes in compared_data['teachers'].items():
                for group_key, change_list in changes.items():
                    # Добавляем все изменения для этого преподавателя/группы преподавателей
                    all_changes['teachers'][teacher_key][group_key].extend(change_list)

            for group_key, change_list in compared_data['groups'].items():
                all_changes['groups'][group_key].extend(change_list)

        for group_name in old_map:
            if group_name not in new_map:
                escaped_group_name = self.escape_html(group_name)
                change_message = f"➖ Удалена группа: {escaped_group_name}"
                all_changes["general"].append(change_message)

        # Удаляем дубликаты в финальном результате
        all_changes = self.remove_duplicate_changes(all_changes)
        
        all_changes = {k: v for k, v in all_changes.items() if v}
        
        return dict(all_changes)

    def remove_duplicate_changes(self, all_changes):
        """Удаляет дубликаты изменений из всех секций"""
        result = {
            "general": [],
            "teachers": defaultdict(lambda: defaultdict(list)),
            "groups": defaultdict(list)
        }
        
        # Удаляем дубликаты из general
        seen_general = set()
        for change in all_changes.get("general", []):
            change_key = re.sub(r'<[^>]+>', '', change).strip()
            if change_key not in seen_general:
                seen_general.add(change_key)
                result["general"].append(change)
        
        # Удаляем дубликаты из groups
        for group_key, change_list in all_changes.get("groups", {}).items():
            seen_changes = set()
            for change in change_list:
                change_key = re.sub(r'<[^>]+>', '', change).strip()
                if change_key not in seen_changes:
                    seen_changes.add(change_key)
                    result["groups"][group_key].append(change)
        
        # Удаляем дубликаты из teachers (сохраняя группировку преподавателей)
        for teacher_key, group_changes in all_changes.get("teachers", {}).items():
            seen_group_changes = {}
            for group_key, change_list in group_changes.items():
                seen_changes = set()
                unique_changes = []
                for change in change_list:
                    change_key = re.sub(r'<[^>]+>', '', change).strip()
                    if change_key not in seen_changes:
                        seen_changes.add(change_key)
                        unique_changes.append(change)
                
                if unique_changes:
                    result["teachers"][teacher_key][group_key] = unique_changes
        
        return result

    def compare_data(self, old_data, new_data, group_name):
        """Сравнивает данные по содержанию, а не по координатам"""
        old_records = self.prepare_records_by_key(old_data)
        new_records = self.prepare_records_by_key(new_data)
        
        teacher_changes = defaultdict(lambda: defaultdict(list))
        group_changes = defaultdict(list)
        
        old_keys = set(old_records.keys())
        new_keys = set(new_records.keys())
        
        # Ключи, которые есть в обоих наборах
        common_keys = old_keys.intersection(new_keys)
        
        # Проверяем изменения аудитории для общих записей
        for key in common_keys:
            old_record = old_records[key]
            new_record = new_records[key]
            
            old_room_norm = self.normalize_room(old_record["room"])
            new_room_norm = self.normalize_room(new_record["room"])
            
            if old_room_norm != new_room_norm:
                escaped_group_name = self.escape_html(group_name)
                link = self.create_hyperlink(new_record["cell"], new_data['sheet_id'])
                
                old_room = self.escape_html(old_room_norm)
                new_room = self.escape_html(new_room_norm)
                highlighted_new = self.highlight_changes(old_room, new_room)
                
                change_message = (
                    f"  {self.escape_html(new_record['time'])} ⚠️ Изменена аудитория: "
                    f"{old_room} → {highlighted_new} {link}"
                )
                
                group_key = escaped_group_name if escaped_group_name else "без группы"
                group_changes[group_key].append(change_message)
                
                # Сохраняем преподавателей как единую группу (не разделяем)
                teacher_key = self.escape_html(new_record["teacher"]) if new_record["teacher"] else "без преподавателя"
                teacher_changes[teacher_key][group_key].append(change_message)
        
        # Находим похожие записи (для случаев небольших изменений в тексте)
        matched_old_keys = set()
        matched_new_keys = set()
        
        for old_key, old_record in old_records.items():
            if old_key in matched_old_keys:
                continue
                
            for new_key, new_record in new_records.items():
                if new_key in matched_new_keys:
                    continue
                    
                # Проверяем похожесть записи
                if (self.similar_strings(old_record["time"], new_record["time"]) and
                    self.similar_strings(old_record["subject"], new_record["subject"]) and
                    self.similar_strings(old_record["teacher"], new_record["teacher"])):
                    
                    # Это похожие записи, проверяем аудиторию
                    old_room_norm = self.normalize_room(old_record["room"])
                    new_room_norm = self.normalize_room(new_record["room"])
                    
                    if old_room_norm != new_room_norm:
                        escaped_group_name = self.escape_html(group_name)
                        link = self.create_hyperlink(new_record["cell"], new_data['sheet_id'])
                        
                        old_room = self.escape_html(old_room_norm)
                        new_room = self.escape_html(new_room_norm)
                        highlighted_new = self.highlight_changes(old_room, new_room)
                        
                        change_message = (
                            f"  {self.escape_html(new_record['time'])} ⚠️ Изменена аудитория: "
                            f"{old_room} → {highlighted_new} {link}"
                        )
                        
                        group_key = escaped_group_name if escaped_group_name else "без группы"
                        group_changes[group_key].append(change_message)
                        
                        # Сохраняем преподавателей как единую группу
                        teacher_key = self.escape_html(new_record["teacher"]) if new_record["teacher"] else "без преподавателя"
                        teacher_changes[teacher_key][group_key].append(change_message)
                    
                    matched_old_keys.add(old_key)
                    matched_new_keys.add(new_key)
                    break
        
        # Удаленные записи (ключи, которые есть только в старом)
        for old_key in old_keys - new_keys:
            if old_key not in matched_old_keys:
                old_record = old_records[old_key]
                escaped_group_name = self.escape_html(group_name)
                link = self.create_hyperlink(old_record["cell"], old_data['sheet_id'])
                
                change_message = (
                    f"  {self.escape_html(old_record['time'])} ❌ Удалена аудитория: "
                )
                
                
                change_message += f"{self.escape_html(old_record['room'])} {link}"
                
                group_key = escaped_group_name if escaped_group_name else "без группы"
                group_changes[group_key].append(change_message)
                
                # Сохраняем преподавателей как единую группу
                teacher_key = self.escape_html(old_record["teacher"]) if old_record["teacher"] else "без преподавателя"
                teacher_changes[teacher_key][group_key].append(change_message)
        
        # Новые записи (ключи, которые есть только в новом)
        for new_key in new_keys - old_keys:
            if new_key not in matched_new_keys:
                new_record = new_records[new_key]
                escaped_group_name = self.escape_html(group_name)
                link = self.create_hyperlink(new_record["cell"], new_data['sheet_id'])
                
                change_message = (
                    f"  {self.escape_html(new_record['time'])} ✅ Добавлена аудитория: "
                )
                
                
                change_message += f"{self.escape_html(new_record['room'])} {link}"
                
                group_key = escaped_group_name if escaped_group_name else "без группы"
                group_changes[group_key].append(change_message)
                
                # Сохраняем преподавателей как единую группу
                teacher_key = self.escape_html(new_record["teacher"]) if new_record["teacher"] else "без преподавателя"
                teacher_changes[teacher_key][group_key].append(change_message)
        
        return {
            'groups': group_changes,
            'teachers': teacher_changes,
            }
    
    def split_teachers(self, s: str):
        """Разделяет строку с преподавателями на список"""
        if not s:
            return []
        s = s.replace("\n", ",")
        teachers = []
        seen = set()
        for teacher in s.split(","):
            teacher_clean = teacher.strip()
            if teacher_clean and teacher_clean not in seen:
                seen.add(teacher_clean)
                teachers.append(teacher_clean)
        return teachers