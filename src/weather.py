from datetime import datetime

import requests

WEATHER_CODES = {
    0: "Ясно",
    1: "Преимущественно ясно",
    2: "Переменная облачность",
    3: "Пасмурно",
    61: "Дождь",
    71: "Снег",
    95: "Гроза",
}


def get_today_weather(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "weathercode",
        ],
        "current_weather": True,
        "timezone": "auto",
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    daily = r.json()["daily"]
    current = r.json()["current_weather"]

    return {
        "t_min": daily["temperature_2m_min"][0],
        "t_max": daily["temperature_2m_max"][0],
        "code": daily["weathercode"][0],
        "current_temp": current["temperature"],
        "current_wind": current["windspeed"],
        "current_time": datetime.fromisoformat(current["time"]).strftime(
            "%H:%M, %d %B"
        ),
    }


def format_weather(w: dict) -> str:
    desc = WEATHER_CODES.get(w["code"], "Неизвестно")
    now_time = datetime.now().strftime("%H:%M:%S, %d %B")

    return (
        f"🌡 Сейчас: {w['current_temp']}°C\n\n"
        f"🕒 Данные на {w['current_time']}\n\n"
        f"🗓 Проверено в {now_time}\n\n"
        f"↕️ Сегодня от {w['t_min']}°C до {w['t_max']}°C\n\n"
        f"💨 Скорость ветра: {w['current_wind']} m/s\n\n"
        f"🌤 {desc}"
    )
