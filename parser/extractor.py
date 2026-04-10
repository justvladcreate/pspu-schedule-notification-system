# [file name]: extractor.py
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from pathlib import Path
import time
import re
import aiofiles
import asyncio
import logging

logger = logging.getLogger(__name__)


class DataExtractor:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.file_id = "1_fsm-OxH9E9LgHnLC0iju5OlaHIv0agmM87GLvRKIAg"
        current_dir = Path(__file__).resolve().parent.parent
        self.token_file = current_dir / 'private' / 'token.json'
        self.credentials_file = current_dir / 'private' / 'credentials.json'

    async def get_service(self):
        creds = None
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.SCOPES)
        except:
            pass
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), self.SCOPES)
                creds = flow.run_local_server(port=0)
            async with aiofiles.open(self.token_file, 'w') as token:
                await token.write(creds.to_json())
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return service, creds

    async def get_sheets_metadata(self):
        service, creds = await self.get_service()
        sheets_service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

        try:
            spreadsheet = sheets_service.spreadsheets().get(
                spreadsheetId=self.file_id
            ).execute()

            sheets_metadata = {}
            for sheet in spreadsheet.get('sheets', []):
                sheet_props = sheet['properties']
                sheets_metadata[sheet_props['title']] = {
                    'sheetId': sheet_props['sheetId'],
                    'title': sheet_props['title'],
                    'index': sheet_props['index'],
                    'gid': sheet_props['sheetId']
                }

            return sheets_metadata

        except Exception as e:
            logger.error(f"Ошибка при получении метаданных листов: {e}")
            return {}

    def _sync_download(self, excel_path):
        creds = None
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.SCOPES)
        except:
            pass
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        request = service.files().export_media(
            fileId=self.file_id,
            mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        with open(excel_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download progress: {int(status.progress() * 100)}%")

    async def download_file(self, excel_path):
        await asyncio.to_thread(self._sync_download, excel_path)

    def delete_old_file(self, file_path, max_time=600):
        path = Path(file_path)
        if not path.exists():
            return
        file_time = path.stat().st_mtime
        current_time = time.time()
        if current_time - file_time > max_time:
            old_file_path = path.parent / f"old_{path.name}"
            if old_file_path.exists():
                old_file_path.unlink()
            path.rename(old_file_path)

    async def extract(self, file_path):
        sheets_metadata = await self.get_sheets_metadata()
        wb = load_workbook(str(file_path), data_only=True)

        groups_info = {}

        for sheet_name in wb.sheetnames[1:]:  # пропускаем первый лист
            ws = wb[sheet_name]

            sheet_gid = None
            if sheet_name in sheets_metadata:
                sheet_gid = sheets_metadata[sheet_name]['gid']

            group_info = self.extraction(ws, sheet_gid)
            if group_info:
                groups_info.update(group_info)

        wb.close()
        return groups_info

    def is_grey_font(self, cell):
        """Проверяет, серый ли шрифт у ячейки"""
        if cell.font and cell.font.color:
            color = cell.font.color
            # theme-based grey
            if color.theme is not None and color.tint and color.tint < 0:
                return True
            # RGB grey — проверяем что R=G=B и значение > 0x80 (светло-серый)
            if color.rgb and isinstance(color.rgb, str) and len(color.rgb) >= 6:
                rgb = color.rgb[-6:]  # последние 6 символов (без alpha)
                try:
                    r, g, b = int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
                    # Серый если R≈G≈B и достаточно светлый (не чёрный)
                    if abs(r - g) < 30 and abs(g - b) < 30 and r > 100:
                        return True
                except ValueError:
                    pass
        return False

    def is_event_row(self, ws, row, start_col, end_col):
        """Проверяет, является ли строка мероприятием (merged, цветной фон)"""
        # Проверяем merged cells
        for merged_range in ws.merged_cells.ranges:
            if (merged_range.min_row <= row <= merged_range.max_row and
                merged_range.min_col <= start_col and merged_range.max_col >= end_col - 1):
                return True

        # Проверяем цвет фона
        cell = ws.cell(row=row, column=start_col + 1)
        if cell.fill and cell.fill.fgColor:
            color = cell.fill.fgColor
            if color.rgb and isinstance(color.rgb, str):
                rgb = color.rgb[-6:]
                if rgb != "000000" and rgb != "FFFFFF" and rgb != "000000":
                    try:
                        r, g, b = int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
                        # Цветной фон (не белый, не чёрный, не прозрачный)
                        if not (r > 240 and g > 240 and b > 240) and not (r < 10 and g < 10 and b < 10):
                            return True
                    except ValueError:
                        pass
        return False

    def get_merged_cell_value(self, ws, row, col):
        """Получает значение ячейки с учётом merged cells"""
        cell = ws.cell(row=row, column=col)
        if cell.value is not None:
            return cell

        # Если ячейка часть merged range, находим значение из верхней левой
        for merged_range in ws.merged_cells.ranges:
            if (merged_range.min_row <= row <= merged_range.max_row and
                merged_range.min_col <= col <= merged_range.max_col):
                return ws.cell(row=merged_range.min_row, column=merged_range.min_col)
        return cell

    def extraction(self, ws, sheet_id):
        """Извлекает расписание из листа openpyxl"""
        start_cells = []
        end_row = None

        for row in ws.iter_rows():
            for cell in row:
                val = str(cell.value).strip() if cell.value else ""
                if "Начало" in val:
                    start_cells.append((cell.row, cell.column))
                if "Декан" in val and end_row is None:
                    end_row = cell.row

        end_cells = []
        for row in ws.iter_rows():
            for cell in row:
                val = str(cell.value).strip().lower() if cell.value else ""
                if "форма обучения /" in val:
                    end_cells.append((end_row, cell.column + 1))

        headers = []
        for row in ws.iter_rows():
            for cell in row:
                val = str(cell.value).strip().lower() if cell.value else ""
                if "семестр" in val:
                    headers.append((cell.row, cell.column))

        groups_info = {}
        min_count = min(len(start_cells), len(end_cells), len(headers))
        if min_count == 0:
            return groups_info

        for i in range(min_count):
            start_cell = start_cells[i]
            end_cell = end_cells[i]
            header_cell = headers[i]

            try:
                header_val = ws.cell(row=header_cell[0], column=header_cell[1]).value
                if not header_val:
                    continue

                group_name, semester, additional_info, session_info, vacation = self._parse_header(str(header_val))
                if not group_name:
                    continue

            except Exception as e:
                logger.error(f"Ошибка при обработке заголовка: {e}")
                continue

            start_row = start_cell[0]
            start_col = start_cell[1]
            end_r = end_cell[0]
            end_col = end_cell[1]

            times = []
            subjects = []
            raw_subjects = []  # сырой текст с ФИО внутри
            teachers = []
            rooms = []
            grey_flags = []
            event_flags = []

            # Определяем столбец дня недели (обычно первый столбец листа)
            day_col = 1
            current_day = ""

            for r in range(start_row + 1, end_r):
                # Получаем день недели
                day_cell = self.get_merged_cell_value(ws, r, day_col)
                if day_cell.value and str(day_cell.value).strip():
                    day_val = str(day_cell.value).strip().upper()
                    if day_val in ("ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ",
                                   "ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"):
                        current_day = day_val

                time_cell = self.get_merged_cell_value(ws, r, start_col)
                time_val = str(time_cell.value).strip() if time_cell.value else ""

                if not time_val:
                    continue

                room_cell = self.get_merged_cell_value(ws, r, end_col - 1)
                room_val = str(room_cell.value).strip() if room_cell.value else ""

                # Проверяем серый шрифт у кабинета
                actual_room_cell = ws.cell(row=r, column=end_col - 1)
                is_room_grey = self.is_grey_font(actual_room_cell)

                # Собираем текст предмета из всех колонок между time и room
                subject_parts = []
                is_grey = False
                for c in range(start_col + 1, end_col - 1):
                    sc = ws.cell(row=r, column=c)
                    if sc.value:
                        subject_parts.append(str(sc.value).strip())
                        if self.is_grey_font(sc):
                            is_grey = True

                subject_text = " ".join(subject_parts).strip()
                if not subject_text:
                    continue

                # Серый предмет ИЛИ серый кабинет — пропускаем
                if is_grey or is_room_grey:
                    continue

                # Проверяем мероприятие
                is_event = self.is_event_row(ws, r, start_col, end_col)

                # Сохраняем сырой текст (с ФИО) для посегментного разбора
                raw_subject_text = subject_text

                # Извлекаем ФИО преподавателей (для обратной совместимости)
                teachers_text, subject_text = self.extract_and_remove_title_fio(subject_text)
                if teachers_text is None:
                    teachers_text = ""
                else:
                    teachers_text = ", ".join(teachers_text)

                # Пропускаем строки без преподавателя (нет ФИО = не парсим)
                if not teachers_text and not is_event:
                    continue

                if current_day:
                    time_val = f"{current_day} {time_val}"

                # Адреса ячеек
                time_cell_addr = f"{get_column_letter(start_col)}{r}"
                subject_cell_addr = f"{get_column_letter(start_col + 1)}{r}"
                room_cell_addr = f"{get_column_letter(end_col - 1)}{r}"

                times.append({"cell": time_cell_addr, "value": time_val})
                subjects.append({"cell": subject_cell_addr, "value": subject_text})
                raw_subjects.append({"cell": subject_cell_addr, "value": raw_subject_text})
                rooms.append({"cell": room_cell_addr, "value": room_val})
                teachers.append({"cell": subject_cell_addr, "value": teachers_text})
                grey_flags.append(is_grey)
                event_flags.append(is_event)

            if times and subjects and rooms:
                groups_info[group_name] = {
                    "sheet_id": sheet_id,
                    "semester": semester,
                    "additional_info": additional_info,
                    "session": session_info,
                    "vacation": vacation,
                    "times": times,
                    "subjects": subjects,
                    "raw_subjects": raw_subjects,
                    "teachers": teachers,
                    "rooms": rooms,
                    "grey_flags": grey_flags,
                    "event_flags": event_flags,
                }

        return groups_info

    def _parse_header(self, header):
        """Парсит заголовок группы"""
        group_name = ""
        semester = None
        additional_info = ""
        session_info = ""
        vacation = ""

        if "семестр" not in header.lower():
            return group_name, semester, additional_info, session_info, vacation

        lines = [line.strip() for line in header.split("\n") if line.strip()]
        if len(lines) < 2:
            return group_name, semester, additional_info, session_info, vacation

        group_name = lines[0]
        group_name = self.clean_group_name(group_name)
        semester = lines[1]

        try:
            session_index = next(i for i, line in enumerate(lines) if "Экзаменационная сессия" in line)
            vacation_index = next(i for i, line in enumerate(lines) if "Каникулы" in line)
            additional_info = "\n".join(lines[2:session_index])
            session_info = lines[session_index]
            vacation = lines[vacation_index]
        except StopIteration:
            pass

        return group_name, semester, additional_info, session_info, vacation

    def extract_and_remove_title_fio(self, text):
        pattern = r'(?:\b[А-ЯЁа-яё\-]{1,20}\.\s*)?\b([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)*)\s+([А-ЯЁ])\.\s*([А-ЯЁ])\.?'
        regex = re.compile(pattern)

        matches = []
        seen_fios = set()

        for m in regex.finditer(text):
            surname = m.group(1)
            first_initial = m.group(2)
            second_initial = m.group(3)
            normalized_fio = f"{surname} {first_initial}.{second_initial}."
            normalized_fio_yo = normalized_fio.replace('ё', 'е').replace('Ё', 'Е')

            if normalized_fio_yo not in seen_fios:
                seen_fios.add(normalized_fio_yo)
                matches.append(normalized_fio_yo)

        cleaned = regex.sub('', text)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        cleaned = re.sub(r'\s+([,.:;])', r'\1', cleaned)
        cleaned = cleaned.strip()

        return matches, cleaned

    def clean_group_name(self, group_name):
        bracket_index = group_name.find(' (')
        if bracket_index != -1:
            return group_name[:bracket_index].strip()
        return group_name.strip()
