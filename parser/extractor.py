# [file name]: extractor.py
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pandas as pd
from pathlib import Path
import time
import re
import aiofiles
import asyncio

class DataExtractor:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.file_id = "1_fsm-OxH9E9LgHnLC0iju5OlaHIv0agmM87GLvRKIAg"
        current_dir = Path(__file__).resolve().parent.parent
        self.token_file = current_dir / 'private\\token.json'
        self.credentials_file = current_dir / 'private\\credentials.json'

    async def get_service(self):
        creds = None
        try:
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        except:
            pass
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            async with aiofiles.open(self.token_file, 'w') as token:
                await token.write(creds.to_json())
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return service, creds  # возвращаем и creds
    
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
            print(f"Ошибка при получении метаданных листов: {e}")
            return {}

    def _sync_download(self, excel_path):
        # Получаем учётные данные синхронно
        creds = None
        try:
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        except:
            pass
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Сохраняем токен синхронно
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        # Строим сервис и скачиваем
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
        
        xls = pd.ExcelFile(file_path)
        groups_info = {}
        
        for n, sheet_name in enumerate(xls.sheet_names[1:]):
            n = n + 1
            df = xls.parse(n)
            
            sheet_gid = None
            if sheet_name in sheets_metadata:
                sheet_gid = sheets_metadata[sheet_name]['gid']
            
            group_info = self.extraction(df, sheet_gid)
            if not group_info: 
                continue
            groups_info.update(group_info)
            
        return groups_info     

 
    
    def extraction(self, df, sheet_id):
        start_cells = []
        for i, row in df.iterrows():
            for j, cell in enumerate(row):
                if "Начало" in str(cell).strip():
                    start_cells.append((i, j))

        end_row = None
        end_cells = []
        for i, row in df.iterrows():
            for j, cell in enumerate(row):
                if "Декан" in str(cell).strip():
                    end_row = i
                    break
            if end_row:
                break

        for i, row in df.iterrows():
            for j, cell in enumerate(row):
                if "форма обучения /" in str(cell).strip().lower():
                    end_cells.append((end_row,j+1))

        headers = []
        for i, row in df.iterrows():
            for j, cell in enumerate(row):
                if "семестр" in str(cell).strip().lower():
                    headers.append((i,j))        

        groups_info = {}
        
        min_count = min(len(start_cells), len(end_cells), len(headers))

        
        if min_count == 0:
            return groups_info

        for i in range(min_count):
            
            start_cell = start_cells[i]
            end_cell = end_cells[i]
            header_cell = headers[i]

            try:
                header = df.iloc[header_cell[0], header_cell[1]]

                group_name = ""
                semester = None
                additional_info = ""
                session = ""
                vacation = ""

                if "семестр" in str(header).lower():
                    lines = [line.strip() for line in str(header).split("\n") if line.strip()]

                    if len(lines) >= 2:
                        group_name = lines[0]
                        group_name = self.clean_group_name(group_name)
                        semester = lines[1]

                        try:
                            session_index = next(i for i, line in enumerate(lines) if "Экзаменационная сессия" in line)
                            vacation_index = next(i for i, line in enumerate(lines) if "Каникулы" in line)

                            additional_info = "\n".join(lines[2:session_index])
                            session = lines[session_index]
                            vacation = lines[vacation_index]
                        except StopIteration:
                            print("Не найдены сессия или каникулы в заголовке")
                    else:
                        print(f"Недостаточно строк в заголовке: {len(lines)}")
            except Exception as e:
                print(f"Ошибка при обработке заголовка: {e}")
                continue
            
            if not group_name:
                print("Не удалось определить номер группы, пропускаем")
                continue

            try:
                subset = df.iloc[start_cell[0]:end_cell[0], start_cell[1]:end_cell[1]]
            except Exception as e:
                print(f"Ошибка при создании subset: {e}")
                continue

            # Новая структура: списки словарей с ячейкой и значением
            times = []
            subjects = []
            teachers = []
            rooms = []

            for row in range(1, subset.shape[0]-1):
                if row >= subset.shape[0]:
                    break
                    
                abs_row = start_cell[0] + row + 1
                time_col = start_cell[1]
                subject_col = start_cell[1] + 1
                room_col = end_cell[1] - 1
                
                try:
                    time_val = subset.iloc[row, 0]
                    if pd.isna(time_val) or str(time_val).strip() == "":
                        continue

                    room_val = subset.iloc[row, -1]
                    if pd.isna(room_val) or str(room_val).strip() == "":
                        continue

                    subject_vals = subset.iloc[row, 1:-1]
                    subject_text = " ".join([str(x).strip() for x in subject_vals if pd.notna(x)]).strip()
                    if not subject_text:
                        continue
                    
                    teachers_text, subject_text = self.extract_and_remove_title_fio(subject_text)
                    
                    if teachers_text is None:
                        teachers_text = ""
                    else:
                        teachers_text = ", ".join(teachers_text)

                    # Добавляем день недели
                    day_of_week = ""
                    df.iloc[:, 0] = df.iloc[:, 0].ffill()
                    left_col_val = df.iloc[abs_row, 0]
                    if pd.notna(left_col_val) and str(left_col_val).strip():
                        day_of_week = str(left_col_val).strip().upper()
                    
                    if day_of_week:
                        time_val = f"{day_of_week} {time_val}"

                    # Создаем записи с ячейками
                    time_cell = self.get_cell_address(abs_row, time_col)
                    subject_cell = self.get_cell_address(abs_row, subject_col)
                    room_cell = self.get_cell_address(abs_row, room_col)

                    times.append({"cell": time_cell, "value": str(time_val).strip()})
                    subjects.append({"cell": subject_cell, "value": subject_text})
                    rooms.append({"cell": room_cell, "value": str(room_val).strip()})
                    teachers.append({"cell": subject_cell, "value": teachers_text})
                    
                except Exception as e:
                    print(f"Ошибка при обработке строки {row}: {e}")

            if times and subjects and rooms:
                    
                groups_info[group_name] = {
                    "sheet_id": sheet_id,
                    "semester": semester,
                    "additional_info": additional_info,
                    "session": session,
                    "vacation": vacation,
                    "times": times,
                    "subjects": subjects,
                    "teachers": teachers,
                    "rooms": rooms
                }
            
        return groups_info

    def extract_and_remove_title_fio(self, text):
        # Обрабатывает: "Иванов И.И.", "Петров-Сидоров А.Б.", "проф. Сидоров В.Г." и т.д.
        pattern = r'(?:\b[А-ЯЁа-яё\-]{1,20}\.\s*)?\b([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)*)\s+([А-ЯЁ])\.\s*([А-ЯЁ])\.?'
        regex = re.compile(pattern)
        
        matches = []
        seen_fios = set()
        
        # Сначала найдем все совпадения
        for m in regex.finditer(text):
            surname = m.group(1)
            first_initial = m.group(2)
            second_initial = m.group(3)
            
            # Формируем нормализованное ФИО: "Иванов И.И."
            normalized_fio = f"{surname} {first_initial}.{second_initial}."
            
            # Для сравнения (убираем ё/е различия)
            normalized_fio_yo = normalized_fio.replace('ё', 'е').replace('Ё', 'Е')
            
            if normalized_fio_yo not in seen_fios:
                seen_fios.add(normalized_fio_yo)
                matches.append(normalized_fio_yo)
        
        # Удаляем найденные ФИО из текста
        cleaned = regex.sub('', text)
        
        # Очистка лишних пробелов и знаков препинания
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        cleaned = re.sub(r'\s+([,.:;])', r'\1', cleaned)
        cleaned = cleaned.strip()
        
        return matches, cleaned

    def get_cell_address(self, row, col):
        col_letter = ""
        col_num = col
        while col_num >= 0:
            col_letter = chr(65 + (col_num % 26)) + col_letter
            col_num = col_num // 26 - 1
            if col_num < 0:
                break
        return f"{col_letter}{row + 1}"

    def clean_group_name(self, group_name):
        bracket_index = group_name.find(' (')
        if bracket_index != -1:
            return group_name[:bracket_index].strip()
        return group_name.strip()