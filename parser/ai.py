from ollama import chat, AsyncClient
import os

# Если файл credentials.json лежит не в той же папке, укажите путь
models: list = ['gemma4:e4b','gemma4:31b-cloud']

OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
# user_prompt = r"""You are going to extract a structured schedule from an input array.
#
# Each array element contains:
#
# "discipline info:" (raw schedule text)
# "rooms info:" (room assignment string)
#
# You must process each element independently.
#
# 1. Core constraints
# Preserve original data EXACTLY.
# NEVER EVER invent, normalize, remove, rewrite or reinterpret.
# Output MUST follow the order of appearance in the input.
# Each element is first split into event branches, then each branch becomes one output line.
# If a field is missing, leave it empty.
# 2. Output fields (fixed schema)
#
# time, dates, discipline, type, subgroup, teachers, rooms
#
# 3. Processing pipeline (mandatory order)
# Step 1 — Segment into event branches (Strict Sequential Parsing)
#
# Trigger Conditions:
# A new branch creates ONLY when one of the following changes occurs in the text flow:
# 1. Discipline name changes.
# 2. Type changes.
# 3. Subgroup changes.
# DO NOT create a branch if discipline name isn't an academic title.
#
# Date Rules:
# - Dates NEVER create a new branch.
# - Multiple dates found within a segment belong to the current active branch.
# - Do not split dates into separate lines.
#
# Step 2 — Extract time
# Format: weekday + start time (e.g., "ПН 11:30")
# Time applies to all branches in the element unless explicitly overridden.
# Step 3 — Extract dates
# Collect all dates associated with the branch.
# Multiple dates are separated by commas.
# Ranges or singles (check examples section) are preserved as-is.
# Do NOT split dates into new branches.
# Never expand, reformat or normalise date substrings. Copy the exact character sequence that describes the date(s).
#
# Example: "9.02, c 16.02 - Иностранный язык"
# dates: "9.02, c 16.02 -"
# discipline: "Иностранный язык"
#
# Step 4 — Extract type
# If a set of parentheses contains one of the following known type keywords, take that string as type and remove it (and its parentheses) from the branch.
# Known type keywords: лек., прак., лаб., лек.прак., семинар, практика (and any equally clear abbreviations you define).
# If no parenthesised type is found, scan the remaining branch text immediately after the date part for the first occurrence of one of those keywords standing alone (not part of a longer word). Treat that token as type and remove it from the discipline text.
# Keep the type exactly as written (no normalisation, no splitting).
# Keep type exactly as written (no normalization, no splitting).
# Step 5 — Extract subgroup
# Look for п/г (or пг) followed by a number. Keep the whole token as subgroup (e.g., п/г 1, пг 2).
# Step 6 — Extract teachers
# Teacher consists only from a title, russian firstname and russian surname
# There are usually one teacher per discipline.
# If no teacher explicitly given, look-ahead inside the current element until a teacher is met.
# Step 7 — Extract discipline
# Discipline is the main academic subject name.
# Include full name even if long.
# Consists of everything that is left in the event branch.
# Step 8 — Assign rooms
# Rooms come only from "rooms info" and are separated by commas.
# Always copy full rooms string as-is.
# 4. Output format (strict, nothing else, no other text)
#
# time: ...; dates: ...; discipline: ...; type: ...; subgroup: ...; teachers: ...; rooms: ...
#
# 5. Priority rules (tie-breakers)
#
# When uncertain:
# Look for solution inside "Examples" section.
# Preserve original meaning in discipline
# Never split dates into structural branches
# Branching is driven ONLY by discipline/type/subgroup changes
#
# Examples:
#
# Input:
# ["discipline info: ПН 11:30\n31.01, с 9.02 - 6.04 Компьютерная и информационная безопасность (лек.), с 13.04-4.05 - прак. рук-ль. Зорин А.А.\nrooms info: IV к. А-231, IV к. Б101, IV к. А306",
# "discipline info: ПН 11:30\nс 18.02 - 3.03, с 17.03 - 31.03, с 14.04 - Программирование и пилотирование БПЛА (лек.\прак.) преп. Шаронов Н.С.\nrooms info: IV к. Б-404, IV к. Б-406"]
#
# Output:
# time: ПН 11:30; dates: 31.01, с 9.02 - 6.04; discipline: Компьютерная и информационная безопасность; type: лек.; subgroup: ; teachers: рук-ль. Зорин А.А.; rooms: IV к. А-231, IV к. Б101, IV к. А306
# time: ПН 11:30; dates: с 13.04 - 4.05; discipline: Компьютерная и информационная безопасность; type: прак.; subgroup: ; teachers: доц. Зорин А.А.; rooms: IV к. А-231, IV к. Б101, IV к. А306
# time: ПН 11:30; dates: с 18.02 - 3.03, с 17.03 - 31.03, с 14.04; discipline: Программирование и пилотирование БПЛА; type: лек.\прак.; subgroup: ; teachers: преп. Шаронов Н.С.; rooms: IV к. Б-404, IV к. Б-406
#
# Input:
# ["discipline info: ПН 11:30\nс 13.02 - Практикум: нереляционные базы данных (прак.) отв. Бочкарев А.М. 03.04 занятия в Сферум. ССЫЛКА на подключение https://sferum.ru/?call_link=2EbHd4SGGihtSrrNaknNiDkAUcSz05jWkicwEUAYv1g\nrooms info: IV к. А101, дистанционно СФЕРУМ"]
#
# Output:
# time: ПН 11:30; dates: с 13.02 -; discipline: Практикум: нереляционные базы данных 03.04 занятия в Сферум. ССЫЛКА на подключение https://sferum.ru/?call_link=2EbHd4SGGihtSrrNaknNiDkAUcSz05jWkicwEUAYv1g; type: прак.; teachers: отв. Бочкарев А.М.; rooms: IV к. А101, дистанционно СФЕРУМ
#
# Input:
# ["discipline info: ПН 13:30\nс 13.02 базы данных (лек.) п/г 1 20.02 базы данных (прак.) п/г 2 доц. Чуприна А.М.\nrooms info: IV к. А101, IV к. А103"]
#
# Output:
# time: ПН 13:30; dates: с 13.02; discipline: базы данных; type: лек.; subgroup: п/г 1 ; teachers: доц. Чуприна А.М.; rooms: IV к. А101, IV к. А103
# time: ПН 13:30; dates: 20.02; discipline: базы данных; type: прак.; subgroup: п/г 2 ; teachers: доц. Чуприна А.М.; rooms: IV к. А101, IV к. А103
#
# Now process this schedule data:
# {data}
# """

user_prompt = """You are a parser for university schedules. You receive one or more input strings, each containing a discipline info line and a rooms info line. For each input string, output one or more structured lines in the strict format:

text
time: <time>; dates: <dates>; discipline: <discipline>; type: <type>; subgroup: <subgroup>; teachers: <teachers>; rooms: <rooms>
Fields are separated by ;. If a field is missing, leave it empty after the colon.

Core Principles
Preserve the original text – never invent, normalise, or rewrite.

Output order must follow the order of the branches inside each input string.

Branching is driven only by a change in discipline, type, or subgroup – never by a change in dates.

Step‑by‑Step Processing
1. Segment into event branches
A new branch is created exclusively when one of these three things changes:

Discipline name (the main subject, not including notes like (ТЕСТИРОВАНИЕ))

Class type (лек., прак., лаб., лек.прак., or equivalent standalone keywords)

Subgroup (п/г 1, п/г 2)

Dates, room changes, or remarks (ЯВКА, ЭКСКУРСИЯ, etc.) never create a new branch.

When scanning the text from left to right, start one branch for the first combination of (discipline, type, subgroup). Whenever you encounter a later piece that clearly belongs to a different discipline, type, or subgroup, close the current branch and start a new one. All dates seen while a branch is active belong to that branch.

Example of branching:

text
2.02 - 6.04 Иностранный язык (прак.), п/г 1 ст. преп. Карсукова Н.К. 16.02 - 6.04 Иностранный язык (прак.), п/г 2 преп. Марченко О.В.
→ Branch 1: discipline Иностранный язык, type прак., subgroup п/г 1 (dates 2.02 - 6.04)
→ Branch 2: same discipline and type but subgroup changed to п/г 2, so new branch (dates 16.02 - 6.04)

Do not split into a new branch when the discipline name remains the same and only the date changes, even if a standalone прак. or лек. appears later that refers to the same discipline with no actual type change.

2. Extract the time
Take the first line after discipline info:. It contains the day of the week and the start time (e.g., ПН 09:45). This time applies to all branches derived from that input string.

3. Extract the dates for each branch
Within a branch, collect all date expressions from the start until the discipline name begins. Dates are written as:

single dates: 13.02

comma lists: 3.02, 10.02

ranges: 9.02 - 7.07

mixed: 11.02 - 15.04, 22.04 - 29.06

If a stray preposition like в appears right after the date part (e.g., 25.04 в), drop that в from the date string (it is not a date). The resulting dates field contains only the pure date expression(s), exactly as in the original, joined by commas if multiple.

4. Extract the class type
Look for the type in two ways, in order:

a) Parenthesised type: If an abbreviation inside parentheses consists only of the tokens лек., прак., лаб. (possibly with dots and spaces), that is the type.
Collapse spaces: (лек. прак.) → type лек.прак.; (лаб. прак) → лаб.прак.; (лек.) → лек..
Remove those parentheses and their content from the remaining text.

b) Standalone keyword: If no parenthesised type was found, look immediately after the date part for a standalone word that is a known type keyword: лек., прак., лаб., лек.прак., семинар, практика. If found, take it as the type and remove it from the discipline text.

If the parentheses contain anything else (e.g., (ТЕСТИРОВАНИЕ), (ЗАЧЕТ), (ДЕБАТЫ)), do not treat it as type; keep those parentheses as part of the discipline name.

5. Extract the subgroup
Find the pattern п/г (or пг) optionally followed by a space and a digit (usually 1 or 2). Store the digit (or the whole token, e.g., п/г 1) in subgroup and remove that fragment from the text.

6. Extract the teachers
Teacher names consist of a title (one of ст.преп., ст. преп., доц., преп., проф., асс., рук-ль., отв.) followed by a Russian surname and initials (e.g., Карсукова Н.К.). If multiple titles/names are present, join them with commas.

Important cleaning: If the text after the title contains an entirely uppercase side‑note (e.g., ЯВКА, СТУДЕНТОВ, ССЫЛКА, ЭКСКУРСИЯ, КОНСУЛЬТАЦИЯ, БЫТЬ), truncate the teacher string just before that note.

If no teacher appears in the branch, look ahead to later parts of the same element’s text (if available) – sometimes the teacher is given only after all branches. If still not found, leave teachers empty.

7. Assemble the discipline
After removing the date part, type parentheses, subgroup token, and teacher string, the remaining text is the discipline. Trim extra spaces, commas, or leading dots. If the discipline includes parenthesised notes like (ТЕСТИРОВАНИЕ) or trailing comments like - 8ч, leave them as part of the discipline name.

8. Assign rooms
Take the full string from the rooms info line (after the colon). It applies to all branches of that input string. If the rooms line is missing, leave rooms empty.

Output Format
For each branch, output exactly one line:

text
time: <time>; dates: <dates>; discipline: <discipline>; type: <type>; subgroup: <subgroup>; teachers: <teachers>; rooms: <rooms>;
No other text. Fields are separated by ;.

Priority Rules (in case of doubt)
Preserve the original sequence and text.

Never split a branch because of a date change.

Branch only when discipline, type, or subgroup changes.

If a type keyword appears ambiguous, rely on the parenthesised form first.

Examples
Example 1 – single element, multiple branches
Input:

text
discipline info: ПН 15:15
2.02 - 6.04 Иностранный язык (прак.), п/г 1 ст. преп. Карсукова Н.К. 16.02 - 6.04 Иностранный язык (прак.), п/г 2 преп. Марченко О.В.
rooms info: IV к. А216, IV к. А224
Output:

text
time: ПН 15:15; dates: 2.02 - 6.04; discipline: Иностранный язык; type: прак.; subgroup: п/г 1; teachers: ст. преп. Карсукова Н.К.; rooms: IV к. А216, IV к. А224
time: ПН 15:15; dates: 16.02 - 6.04; discipline: Иностранный язык; type: прак.; subgroup: п/г 2; teachers: преп. Марченко О.В.; rooms: IV к. А216, IV к. А224
Example 2 – note inside parentheses kept
Input:

text
discipline info: ВТ 15:15
24.02 - 21.04 Общая и социальная психология (прак.) доц. Баландина Л.Л. 28.04 Общая и социальная психология (ТЕСТИРОВАНИЕ) доц. Баландина Л.Л.
rooms info: II к. 408
Output:

text
time: ВТ 15:15; dates: 24.02 - 21.04; discipline: Общая и социальная психология; type: прак.; subgroup: ; teachers: доц. Баландина Л.Л.; rooms: II к. 408
time: ВТ 15:15; dates: 28.04; discipline: Общая и социальная психология (ТЕСТИРОВАНИЕ); type: ; subgroup: ; teachers: доц. Баландина Л.Л.; rooms: II к. 408
Example 3 – stray preposition dropped
Input:

text
discipline info: СБ 11:30
25.04 в История России (прак.) преп. Штейников С.Н.
rooms info: II к. 302
Output:

text
time: СБ 11:30; dates: 25.04; discipline: История России; type: прак.; subgroup: ; teachers: преп. Штейников С.Н.; rooms: II к. 302
Apply these instructions to every input string you receive.

Input data:
{data}"""

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