import json
import os

import telebot

from weather import format_weather, get_today_weather

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, "../token.txt")
DATA_FILE = os.path.join(BASE_DIR, "../data/users.json")

try:
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        TOKEN = f.readline().strip()
    if not TOKEN:
        raise ValueError("TOKEN EMPTY")
except FileNotFoundError:
    raise RuntimeError(f"File with TOKEN not FOUND: {TOKEN_PATH}")
except ValueError as e:
    raise ValueError(f"Errors in TOKEN: {e}")


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        knownUsers.append(uid)
        userStep[uid] = 0
        save_users()
        print('Detected new user, who hasn`t used "/start" ')
        return 0


def listener(message):
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
    if not os.path.exists(DATA_FILE):
        return [], {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return [], {}

    return data.get("known_users", []), {
        int(k): v for k, v in data.get("user_step", {}).items()
    }


def save_users():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "known_users": knownUsers,
                "user_step": userStep,
            },
            f,
            indent=2,
        )


bot = telebot.TeleBot(TOKEN)
bot.set_update_listener(listener)

knownUsers, userStep = load_users()

commands = {
    "start": "Get used to the bot",
    "help": "Gives you information about the available commands",
    "wether": "Gives you weather for the day",
}

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
    help_text = "The following command are available: \n"
    for command in commands:
        help_text += "/" + command + ": "
        help_text += commands[command] + "\n"
    bot.send_message(cid, help_text)


@bot.message_handler(commands=["wether"])
def command_wether(m):
    cid = m.chat.id
    w = get_today_weather(55.0344, 82.9434)
    bot.send_message(cid, format_weather(w))


@bot.message_handler(content_types=["text"])
def command_default(m):
    cid = m.chat.id
    bot.send_message(
        cid,
        "I don't understand \"" + m.text + '"\nMaybe try the help page at /help',
    )


bot.infinity_polling()
