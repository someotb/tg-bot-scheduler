import json
import re

import requests

from config import LOGIN, PASSWORD

LOGIN_URL = "https://sibsutis.ru/auth/?login=yes"
PERSONAL_URL = "https://sibsutis.ru/company/personal/"
SCHEDULE_URL = "https://sibsutis.ru/students/schedule/?type=student&group="
GROUP_ID  = "https://sibsutis.ru/ajax/get_groups_soap.php"

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0",
    }
)


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

def get_group_id(group_name: str) -> dict:
    r = session.get(GROUP_ID, params={"search_group": group_name})
    return r.json().get("results")

def format_schedule(schedule: dict) -> str:
    """
    Форматирует расписание для вывода в телеграм
    """
    if not schedule:
        return "📅 Расписание не найдено"

    output = []

    weekdays = {
        "Понедельник": "ПН",
        "Вторник": "ВТ",
        "Среда": "СР",
        "Четверг": "ЧТ",
        "Пятница": "ПТ",
        "Суббота": "СБ",
        "Воскресенье": "ВС",
    }

    for day_idx in sorted(schedule.keys()):
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

        output.append(f"\n<b>📆 {weekday_full} ({weekday})</b>")
        output.append("─" * 30)

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
                classroom = sub.get("CLASSROOM", "")

                type_short = {
                    "Лекционные занятия": "Лекция",
                    "Практические занятия": "Практика",
                    "Лабораторные занятия": "Лабораторная",
                }.get(lesson_type, lesson_type[:3])

                pair_text = f"\n<b>{time_start}-{time_end}</b> | {type_short}\n"
                pair_text += f"📚 {discipline}\n"

                if teacher:
                    pair_text += f"👨‍🏫 {teacher}\n"
                if classroom:
                    pair_text += f"🚪 {classroom}"

                output.append(pair_text)

    if not output:
        return "📅 Расписание пустое"

    return "\n".join(output).strip()
