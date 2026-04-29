from ollama import chat, AsyncClient
import os

# Если файл credentials.json лежит не в той же папке, укажите путь
models: list = ['gemma4:e4b','gemma4:31b-cloud']

OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
user_prompt = r"""You are going to extract a structured schedule from an input array.

Each array element contains:

"discipline info:" (raw schedule text)
"rooms info:" (room assignment string)

You must process each element independently.

1. Core constraints
Preserve original data EXACTLY. Do not invent, normalize, remove, rewrite or reinterpret beyond these rules.
Output MUST follow the order of appearance in the input.
Each element is first split into event branches, then each branch becomes one output line.
If a field is missing, leave it empty.
2. Output fields (fixed schema)

time, dates, discipline, type, subgroup, teachers, comment, rooms

3. Processing pipeline (mandatory order)
Step 1 — Segment into event branches (Strict Sequential Parsing)

Trigger Conditions:
A new branch starts ONLY when one of the following changes occurs in the text flow:
1. Discipline name changes.
2. Type changes (content inside parentheses).
3. Subgroup changes.

Date Rules:
- Dates NEVER create a new branch.
- Multiple dates found within a segment belong to the current active branch.
- Do not split dates into separate lines.

Step 2 — Extract time
Format: weekday + start time (e.g., "ПН 11:30")
Time applies to all branches in the element unless explicitly overridden.
Step 3 — Extract dates
Collect all dates associated with the branch.
Multiple dates are separated by commas.
Ranges or singles (check examples section) are preserved as-is.
Do NOT split dates into new branches.
Step 4 — Extract discipline
Discipline is the main academic subject name.
Include full name even if long.
Non-academic scheduled events are treated as discipline IF they clearly occupy a timetable slot.
Only move text to comment if it is clearly operational (links, instructions, attendance notes).
Step 5 — Extract type
Type is taken ONLY from parentheses if present and is not part of a discipline.
If multiple sets of parentheses exist, the one containing known type keywords takes priority as the 'type'.
Accept values like: лек, прак, лаб, семинар, лек.прак.
Keep type exactly as written (no normalization, no splitting).
Step 6 — Extract subgroup
Subgroup appears near type (e.g., "п/г 1").
Step 7 — Extract teachers
There are usually one teacher per discipline. If no teacher explicitly given, look-ahead inside the current element until a teacher is met.
Step 8 — Extract comment
Include only:

URLs
attendance/organizational instructions
meeting notes
platform instructions
clearly non-academic metadata

Everything else must remain in discipline.

Step 9 — Assign rooms
Rooms come only from "rooms info" and are separated by commas.
Rooms are mapped to branch creation order, not to discipline similarity, teacher position, or subgroup meaning.
If number of rooms equals number of branches → assign 1:1 in order.
Otherwise → repeat full rooms string for each branch.
4. Output format (strict, nothing else, no other text)

time: ...; dates: ...; discipline: ...; type: ...; subgroup: ...; teachers: ...; comment: ...; rooms: ...

5. Priority rules (tie-breakers)

When uncertain:
Look for solution inside "Examples" section.
Preserve original meaning in discipline
Move only clearly operational text into comment
Never split dates into structural branches
Branching is driven ONLY by discipline/type/subgroup changes

Examples:

Input:
["discipline info: ПН 11:30\n31.01, с 9.02 - 6.04 Компьютерная и информационная безопасность (лек.), с 13.04-4.05 - прак. доц. Зорин А.А.\nrooms info: IV к. А-231, IV к. Б101, IV к. А306",
"discipline info: ПН 11:30\nс 18.02 - 3.03, с 17.03 - 31.03, с 14.04 - Программирование и пилотирование БПЛА (лек.\прак.) преп. Шаронов Н.С.\nrooms info: IV к. Б-404, IV к. Б-406"]

Output:
time: ПН 11:30; dates: 31.01, с 9.02 - 6.04; discipline: Компьютерная и информационная безопасность; type: лек.; subgroup: ; teachers: доц. Зорин А.А.; comment: ; rooms: IV к. А-231, IV к. Б101, IV к. А306
time: ПН 11:30; dates: с 13.04 - 4.05; discipline: Компьютерная и информационная безопасность; type: прак.; subgroup: ; teachers: доц. Зорин А.А.; comment: ; rooms: IV к. А-231, IV к. Б101, IV к. А306
time: ПН 11:30; dates: с 18.02 - 3.03, с 17.03 - 31.03, с 14.04; discipline: Программирование и пилотирование БПЛА; type: лек.\прак.; subgroup: ; teachers: преп. Шаронов Н.С.; comment: ; rooms: IV к. Б-404, IV к. Б-406

Input:
["discipline info: ПН 11:30\nс 13.02 - Практикум: нереляционные базы данных (прак.) доц. Бочкарев А.М. 03.04 занятия в Сферум. ССЫЛКА на подключение https://sferum.ru/?call_link=2EbHd4SGGihtSrrNaknNiDkAUcSz05jWkicwEUAYv1g\nrooms info: IV к. А101, дистанционно СФЕРУМ"]

Output:
time: ПН 11:30; dates: с 13.02 -; discipline: Практикум: нереляционные базы данных; type: прак.; teachers: доц. Бочкарев А.М.; comment: 03.04 занятия в Сферум. ССЫЛКА на подключение https://sferum.ru/?call_link=2EbHd4SGGihtSrrNaknNiDkAUcSz05jWkicwEUAYv1g; rooms: IV к. А101, дистанционно СФЕРУМ

Input:
["discipline info: ПН 13:30\nс 13.02 базы данных (лек.) п/г 1 20.02 базы данных (прак.) п/г 2 доц. Чуприна А.М.\nrooms info: IV к. А101, IV к. А103"]

Output:
time: ПН 13:30; dates: с 13.02; discipline: базы данных; type: лек.; subgroup: п/г 1 ; teachers: доц. Чуприна А.М.; comment: ; rooms: IV к. А101
time: ПН 13:30; dates: 20.02; discipline: базы данных; type: прак.; subgroup: п/г 2 ; teachers: доц. Чуприна А.М.; comment: ; rooms: IV к. А103

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