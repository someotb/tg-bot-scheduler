import json
import os
from datetime import datetime

import telebot
from telebot import types

import config
from schedule import format_schedule, get_schedule_html, parse_schedule
from weather import format_weather, get_today_weather

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(BASE_DIR, "../data/users.json")


def about_me():
    text = "I am a bot for experiments, my creator will use me for his own purposes, he hopes that I will become a good helper for him in everyday life, do you think I will justify his trustworthiness?"
    return text


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        knownUsers.append(uid)
        userStep[uid] = 0
        save_users()
        print('Detected new user, who hasn`t used "/start" ')
        return 0


def message_listener(message):
    for m in message:
        if m.content_type == "text":
            print(
                str(m.chat.first_name + " " + m.chat.last_name)
                + " ["
                + str(m.chat.id)
                + "]: "
                + m.text
            )


def load_users():
    if not os.path.exists(USER_FILE):
        return [], {}

    with open(USER_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return [], {}

    return data.get("known_users", []), {
        int(k): v for k, v in data.get("user_step", {}).items()
    }


def save_users():
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "known_users": knownUsers,
                "user_step": userStep,
            },
            f,
            indent=2,
        )


bot = telebot.TeleBot(config.BOT_TOKEN)
bot.set_update_listener(message_listener)
knownUsers, userStep = load_users()
print("------------------Bot Started------------------")


@bot.message_handler(commands=["start"])
def command_start(m):
    cid = m.chat.id
    name = m.chat.first_name + " " + m.chat.last_name
    if cid not in knownUsers:
        knownUsers.append(cid)
        userStep[cid] = 0
        save_users()
        bot.send_message(
            cid, "I'm glad to see you. stranger, i must scan you firstly..."
        )
        bot.send_message(
            cid,
            "The scan is completed!\nI am your humble servant, you can call me nado.\nNice to meet you "
            + name,
        )
        command_help(m)
    else:
        bot.send_message(cid, f"Hi, {name}!")
        command_help(m)


@bot.message_handler(commands=["help"])
def command_help(m):
    cid = m.chat.id
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🌤 Weather", callback_data="weather"),
        types.InlineKeyboardButton("⁉️ About me", callback_data="about"),
        types.InlineKeyboardButton("📆 Schedule", callback_data="schedule"),
    )
    bot.send_message(cid, "That's what I can do for you.", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data in ("weather", "about", "schedule"))
def callbacks(call):
    print(
        f"{call.from_user.first_name} {call.from_user.last_name or ''}"
        f"[{call.from_user.id}]: INLINE -> {call.data}"
    )
    cid = call.message.chat.id
    bot.answer_callback_query(call.id)
    if call.data == "weather":
        w = get_today_weather(55.0344, 82.9434)
        bot.send_message(cid, format_weather(w), parse_mode="HTML")
    elif call.data == "about":
        bot.send_message(cid, about_me())
    elif call.data == "schedule":
        html = get_schedule_html()
        if not html:
            bot.send_message(cid, "❌ Не удалось получить расписание")
            return
        schedule = parse_schedule(html)
        text = format_schedule(schedule)
        bot.send_message(cid, text, parse_mode="HTML")


@bot.message_handler(content_types=["text"])
def command_default(m):
    cid = m.chat.id
    bot.send_message(
        cid,
        "I don't understand \"" + m.text + '"\nMaybe try the help page at /help',
    )


bot.infinity_polling(skip_pending=True, timeout=20)
