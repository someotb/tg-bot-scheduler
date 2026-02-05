import json
import re
from datetime import datetime
from typing import Any

import requests

from config import LOGIN, PASSWORD

LOGIN_URL = "https://sibsutis.ru/auth/?login=yes"
PERSONAL_URL = "https://sibsutis.ru/company/personal/"
SCHEDULE_URL = "https://sibsutis.ru/students/schedule/?type=student&group="
GROUP_ID = "https://sibsutis.ru/ajax/get_groups_soap.php"

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0",
    }
)


def normalize_group_name(name: str) -> str:
    return re.sub(r"[\s\-]", "", name).lower()


def is_logged_in():
    r = session.get(PERSONAL_URL)
    return "logout=yes" in r.text


def bitrix_login():
    r = session.get(LOGIN_URL)
    m = re.search(r"bitrix_sessid'\s*:\s*'([a-f0-9]+)'", r.text)
    if not m:
        return False

    payload = {
        "AUTH_FORM": "Y",
        "TYPE": "AUTH",
        "backurl": "/company/personal/",
        "USER_LOGIN": LOGIN,
        "USER_PASSWORD": PASSWORD,
        "Login": "Войти",
        "sessid": m.group(1),
    }

    session.post(LOGIN_URL, data=payload)
    return is_logged_in()


def ensure_login():
    if not is_logged_in():
        return bitrix_login()
    return True


def get_schedule_html(group_id: str):
    if not ensure_login():
        return None
    return session.get(str(SCHEDULE_URL + group_id)).text


def parse_schedule(html: str) -> dict:
    """
    Парсит расписание из HTML страницы СибГУТИ
    Извлекает данные из строк вида: days[1] = '{"Date":"..."}'
    """
    schedule = {}

    pattern = r"days\[(\d+)\]\s*=\s*\'([^\']+)\'"
    matches = re.findall(pattern, html)

    for idx, json_str in matches:
        try:
            day_data = json.loads(json_str)
            date = day_data.get("Date", "0001-01-01")

            if date == "0001-01-01":
                continue

            schedule[int(idx)] = day_data

        except json.JSONDecodeError:
            continue

    return schedule


def get_group_id(group_name: str) -> list[dict[str, Any]]:
    r = session.get(GROUP_ID, params={"search_group": group_name})
    return r.json().get("results")


def is_even_week(date: datetime | None = None) -> bool:
    if date is None:
        date = datetime.now()
    return date.isocalendar().week % 2 == 0


def is_day_for_current_week(day_idx: int, is_even_week: bool) -> bool:
    if not is_even_week:
        return 8 <= day_idx <= 14
    return 1 <= day_idx <= 7


def format_schedule(schedule: dict) -> str:
    """
    Форматирует расписание для вывода в телеграм
    """
    if not schedule:
        return "📅 Расписание не найдено"

    today = datetime.now()
    weekday_num = today.isoweekday()
    is_even_week = today.isocalendar().week % 2 == 0
    output = []

    weekdays = {
        "Понедельник": 1,
        "Вторник": 2,
        "Среда": 3,
        "Четверг": 4,
        "Пятница": 5,
        "Суббота": 6,
        "Воскресенье": 7,
    }

    for day_idx in sorted(schedule.keys()):
        if not is_day_for_current_week(day_idx, is_even_week):
            continue
        day_data = schedule[day_idx]

        lessons = []
        for cell in day_data.get("ScheduleCell", []):
            if cell.get("Subgroup"):
                for sub in cell["Subgroup"]:
                    if sub.get("DISCIPLINE"):
                        lessons.append(sub)
                        break
                if lessons:
                    break

        if not lessons:
            continue

        first_lesson = lessons[0]
        weekday_full = first_lesson.get("WEEK_DAY", "День")
        weekday = weekdays.get(weekday_full, weekday_full)

        if weekday_num == weekday:
            output.append(f"\n<i><b><u>{weekday_full.upper()}</u></b></i>")

            for cell in day_data.get("ScheduleCell", []):
                time_start = (
                    cell.get("DateBegin", "").split("T")[-1][:5]
                    if "T" in str(cell.get("DateBegin", ""))
                    else ""
                )
                time_end = (
                    cell.get("DateEnd", "").split("T")[-1][:5]
                    if "T" in str(cell.get("DateEnd", ""))
                    else ""
                )

                if not cell.get("Subgroup"):
                    continue

                for sub in cell["Subgroup"]:
                    if not sub.get("DISCIPLINE"):
                        continue

                    discipline = sub.get("DISCIPLINE", "—")
                    lesson_type = sub.get("TYPE_LESSON", "")
                    teacher = sub.get("TEACHER", [""])[0] if sub.get("TEACHER") else ""
                    teacher = teacher.split()
                    res_teacher = teacher[0] + "."
                    if teacher[-3]:
                        res_teacher += teacher[-2][0].upper() + "."
                        res_teacher += teacher[-3][0].upper() + "."
                    elif teacher[-2]:
                        res_teacher += teacher[-2][0].upper() + "."
                    classroom = sub.get("CLASSROOM", "")

                    type_short = {
                        "Лекционные занятия": "Лекция",
                        "Практические занятия": "Практика",
                        "Лабораторные занятия": "Лабораторная",
                    }.get(lesson_type, lesson_type[:3])

                    pair_text = f"\n<u>{time_start}-{time_end} | {type_short}</u>\n"
                    pair_text += f"<b>{discipline}</b>\n"  # Дисциплина жирным
                    if teacher or classroom:
                        pair_text += f"{res_teacher}"
                        if teacher and classroom:
                            pair_text += " | "
                        pair_text += f"<code>{classroom}</code>"

                    output.append(pair_text)

    if not output:
        return "📅 Расписание пустое"

    return "\n".join(output).strip()
