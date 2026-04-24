from ollama import chat, AsyncClient
from ollama import ChatResponse
from datetime import datetime, timedelta
import re
import os

# Если файл credentials.json лежит не в той же папке, укажите путь
models: list = ['gemma4:e4b','gemma4:31b-cloud']

OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
user_prompt = r"""Extract structured schedule from each input array element. Each element has two parts: "discipline info:" and "rooms info:". Produce one line per unique combination of dates and discipline. If a field is missing, leave it empty. Never invent data.

Fields: time, dates, discipline, type, subgroup, teachers, comment, rooms.

- "time" is weekday + start time (e.g. "ПН 11:30").
- "dates" can be multiple, separated by commas.
- "type": лек., прак., лек.прак., etc.
- "teachers": copy from the text. If a teacher is not explicitly given for a specific discipline, use the only teacher in the whole element or the first teacher found after the discipline name.
- "comment": any extra text like "03.04 занятия в Сферум. Ссылка: ...". Preserve URLs.
- "rooms": from "rooms info", separated by commas. Mostly one room correlates to a discipline; if unsure about distribution, keep all rooms together
- Discard entries with empty discipline.
- Output format exactly:
time: ...; dates: ...; discipline: ...; type: ...; subgroup: ...; teachers: ...; comment: ...; rooms: ...

Examples:

Input:
["discipline info: ПН 11:30\n31.01, с 9.02 - 6.04 Компьютерная и информационная безопасность (лек.), с 13.04-4.05 - прак. доц. Зорин А.А.\nrooms info: IV к. А-231, IV к. Б101, IV к. А306",
"discipline info: ПН 11:30\nс 18.02 - 3.03, с 17.03 - 31.03, с 14.04 - Программирование и пилотирование БПЛА (лек.\прак.) преп. Шаронов Н.С.\nrooms info: IV к. Б-404, IV к. Б-406"]

Output:
time: ПН 11:30; dates: 31.01, с 9.02 - 6.04; discipline: Компьютерная и информационная безопасность; type: лек.; subgroup: ; teachers: доц. Зорин А.А.; comment: ; rooms: IV к. А-231, IV к. Б101, IV к. А306
time: ПН 11:30; dates: с 13.04 - 4.05; discipline: Компьютерная и информационная безопасность; type: прак.; subgroup: ; teachers: доц. Зорин А.А.; comment: ; rooms: IV к. А-231, IV к. Б101, IV к. А306
time: ПН 11:30; dates: с 18.02 - 3.03, с 17.03 - 31.03, с 14.04; discipline: Программирование и пилотирование БПЛА; type: лек.прак.; subgroup: ; teachers: преп. Шаронов Н.С.; comment: ; rooms: IV к. Б-404, IV к. Б-406

Input:
["discipline info: ПН 11:30\nс 13.02 - 15.05 Практикум: нереляционные базы данных (прак.) доц. Бочкарев А.М. 03.04 занятия в Сферум. ССЫЛКА на подключение https://sferum.ru/?call_link=2EbHd4SGGihtSrrNaknNiDkAUcSz05jWkicwEUAYv1g\nrooms info: IV к. А101, дистанционно СФЕРУМ"]

Output:
time: ПН 11:30; dates: с 13.02 - 15.05; discipline: Практикум: нереляционные базы данных; type: прак.; teachers: доц. Бочкарев А.М.; comment: 03.04 занятия в Сферум. Ссылка: https://sferum.ru/?call_link=2EbHd4SGGihtSrrNaknNiDkAUcSz05jWkicwEUAYv1g; rooms: IV к. А101, дистанционно СФЕРУМ

Input:
["discipline info: ПН 13:30\nс 13.02 базы данных (лек.) 20.02 базы данных (прак.) доц. Чуприна А.М.\nrooms info: IV к. А101, IV к. А103"]

Output:
time: ПН 13:30; dates: с 13.02; discipline: базы данных; type: лек.; teachers: доц. Чуприна А.М.; comment: ; rooms: IV к. А101
time: ПН 13:30; dates: 20.02; discipline: базы данных; type: прак.; teachers: доц. Чуприна А.М.; comment: ; rooms: IV к. А103


Now process this schedule data:
"""

async def ask_ai(prompt: str = '',model: str = 'gemma4:31b-cloud') -> list[str]:
    #local client
    # response: ChatResponse = chat(model=model, messages=[
    #     {
    #         'role': 'user',
    #         'content': prompt,
    #         'images': [image]
    #     },
    # ])

    # cloud api client
    client = AsyncClient(
        host=OLLAMA_HOST,
        headers={'Authorization': 'Bearer ' + os.environ.get('OLLAMA_API_KEY')}  # если нужен облачный
    )

    #cloud api client
    # client = AsyncClient()

    messages = [
        {
            'role': 'user',
            'content': prompt
        },
    ]
    response = await client.chat(model, messages=messages)

    return response['message']['content'].split("\n")