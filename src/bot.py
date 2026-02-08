import json
import os
from datetime import datetime

from aiogram import BaseMiddleware, Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message, TelegramObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database
from schedule import (
    format_schedule,
    get_group_id,
    get_schedule_html,
    group_name_with_hyphen,
    normalize_group_name,
    parse_schedule,
    valid,
)
from weather import format_weather, get_today_weather

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(os.path.dirname(__file__), "../data/messages.log")

def about_me():
    return (
        "Я - бот для экспериментов, мой создатель будет использовать меня в своих целях, "
        "он надеется, что я стану для него хорошим помощником в повседневной жизни, "
        "как вы думаете, я оправдаю его доверие?"
    )


def groups_keyboard(groups: list):
    groups_sorted = sorted(groups, key=lambda g: g.get("text", ""))
    kb = InlineKeyboardBuilder()
    row_len = 2 if len(groups) < 12 else 4
    for group in groups_sorted:
        gid = str(group.get("id", ""))
        name = str(group.get("text", ""))
        if not gid or not name:
            continue
        kb.add(InlineKeyboardButton(text=name, callback_data=f"group:{gid}"))
    kb.adjust(row_len)
    return kb.as_markup()


async def log_message(message: Message | None):
    if message is None:
        return
    user = message.from_user
    entry = {
        "time": datetime.now().isoformat(),
        "user_id": getattr(user, "id", None),
        "username": getattr(user, "username", None),
        "first_name": getattr(user, "first_name", None),
        "last_name": getattr(user, "last_name", None),
        "text": message.text,
    }

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class UserUpdateMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            cid = user.id
            if not database.user_exists(cid):
                database.add_user(cid)
            
            database.set_username(cid, user.username)
            database.set_firstname(cid, user.first_name)
            database.set_lastname(cid, user.last_name)

        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        try:
            if isinstance(event, Message):
                await log_message(event)

            elif isinstance(event, CallbackQuery):
                user = event.from_user
                entry = {
                    "time": datetime.now().isoformat(),
                    "user_id": getattr(user, "id", None),
                    "username": getattr(user, "username", None),
                    "first_name": getattr(user, "first_name", None),
                    "last_name": getattr(user, "last_name", None),
                    "callback_data": event.data,
                }
                os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"LoggingMiddleware error: {e}")

        return await handler(event, data)


database.init_db()
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
dp.message.middleware(UserUpdateMiddleware())
dp.callback_query.middleware(UserUpdateMiddleware())
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())
print("Bot Started...")


@dp.message(Command(commands=["start"]))
async def command_start(m: types.Message):
    cid = m.chat.id
    name = (m.chat.first_name or "") + " " + (m.chat.last_name or "")
    if not database.user_exists(cid):
        database.add_user(cid)
        await m.answer("Привет, я бот `nado`, надо узнать друг друга поближе, давай просканирую тебя...")
        await m.answer(
            f"Сканирование завершено, рад знакомству {name}!"
        )
        await command_help(m)
    else:
        await m.answer(f"Привет, {name}!")
        await command_help(m)


@dp.message(Command(commands=["help"]))
async def command_help(m: types.Message):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🌤 Погода", callback_data="weather"),
        InlineKeyboardButton(text="⁉️ Обо мне", callback_data="about"),
        InlineKeyboardButton(text="📆 Расписание", callback_data="schedule"),
    )
    await m.answer("Вот, что я могу для тебя сделать.", reply_markup=kb.as_markup())


class GroupForm(StatesGroup):
    waiting_for_group = State()


@dp.message(Command(commands=["group"]))
async def change_group_command(m: types.Message, state: FSMContext):
    await m.answer("Напиши из какой ты группы")
    await state.set_state(GroupForm.waiting_for_group)


@dp.message(GroupForm.waiting_for_group)
async def process_group(m: types.Message, state: FSMContext):
    if not m.text:
        return

    text_clean = normalize_group_name(m.text)
    if not valid(text_clean):
        await m.answer(
            "Некорректное название группы.\n"
            "Разрешены только русские буквы и цифры».\n"
            "Пример: АА000"
        )
        return
    groups = get_group_id(text_clean)
    groups += get_group_id(group_name_with_hyphen(text_clean))

    seen_ids = set()
    groups = [
        g for g in groups if g["id"] not in seen_ids and not seen_ids.add(g["id"])
    ]

    if groups:
        await m.answer("Выбери группу:", reply_markup=groups_keyboard(groups))
    else:
        await m.answer("Группу не нашли. Попробуй ещё раз /group")

    await state.clear()


@dp.callback_query(lambda c: c.data.startswith("group:"))
async def handle_group(call: types.CallbackQuery):
    if not call.data or not call.message:
        return

    gid = call.data.split(":")[1]
    cid = call.message.chat.id
    await call.answer()

    database.set_group(cid, gid)

    html = get_schedule_html(gid)
    if not html:
        await call.message.answer("Не удалось получить расписание")
        return

    schedule = parse_schedule(html)
    text = format_schedule(schedule)
    await call.message.answer(text)


@dp.callback_query(lambda c: c.data in ("weather", "about", "schedule"))
async def callbacks(call: types.CallbackQuery, state: FSMContext):
    if call.message is None:
        return
    await call.answer()
    cid = call.message.chat.id

    if call.data == "weather":
        w = get_today_weather(55.0344, 82.9434)
        await call.message.answer(format_weather(w))
    elif call.data == "about":
        await call.message.answer(about_me())
    elif call.data == "schedule":
        database.add_user(cid)
        gid = database.get_group(cid)
        if gid:
            html = get_schedule_html(str(gid))
            if not html:
                await call.message.answer("Не удалось получить расписание")
                return
            schedule = parse_schedule(html)
            text = format_schedule(schedule)
            await call.message.answer(text)
        else:
            await call.message.answer("Напиши из какой ты группы")
            await state.set_state(GroupForm.waiting_for_group)


@dp.message()
async def command_default(m: types.Message):
    await m.answer(f'Я не понимаю "{m.text}"\nПопробуйте команду /help')


if __name__ == "__main__":
    import asyncio

    asyncio.run(dp.start_polling(bot))
