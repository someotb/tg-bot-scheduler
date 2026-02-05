import os

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database
from schedule import (
    format_schedule,
    get_group_id,
    get_schedule_html,
    normalize_group_name,
    parse_schedule,
)
from weather import format_weather, get_today_weather

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def about_me():
    return (
        "I am a bot for experiments, my creator will use me for his own purposes, "
        "he hopes that I will become a good helper for him in everyday life, "
        "do you think I will justify his trustworthiness?"
    )


def groups_keyboard(groups: list):
    groups_sorted = sorted(groups, key=lambda g: g.get("text", ""))
    kb = InlineKeyboardBuilder()
    row_len = 2 if len(groups) < 12 else 3
    row = []
    for i, group in enumerate(groups_sorted, 1):
        gid = str(group.get("id", ""))
        name = str(group.get("text", ""))
        if not gid or not name:
            continue
        row.append(InlineKeyboardButton(text=name, callback_data=f"group:{gid}"))
        if i % row_len == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.adjust(2)
    return kb.as_markup()


database.init_db()
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

print("------------------Bot Started------------------")


@dp.message(Command(commands=["start"]))
async def command_start(m: types.Message):
    cid = m.chat.id
    name = (m.chat.first_name or "") + " " + (m.chat.last_name or "")
    if not database.user_exists(cid):
        database.add_user(cid)
        await m.answer("I'm glad to see you. stranger, i must scan you firstly...")
        await m.answer(
            f"The scan is completed!\nI am your humble servant, you can call me nado.\nNice to meet you {name}"
        )
        await command_help(m)
    else:
        await m.answer(f"Hi, {name}!")
        await command_help(m)


@dp.message(Command(commands=["help"]))
async def command_help(m: types.Message):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🌤 Weather", callback_data="weather"),
        InlineKeyboardButton(text="⁉️ About me", callback_data="about"),
        InlineKeyboardButton(text="📆 Schedule", callback_data="schedule"),
    )
    await m.answer("That's what I can do for you.", reply_markup=kb.as_markup())


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
        "Пример: АА000")
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
        await call.message.answer("❌ Не удалось получить расписание")
        return

    schedule = parse_schedule(html)
    text = format_schedule(schedule)
    await call.message.answer(text)


@dp.callback_query(lambda c: c.data in ("weather", "about", "schedule"))
async def callbacks(call: types.CallbackQuery, state: FSMContext):
    if call.message is None:
        return

    print(
        f"{call.from_user.first_name} {call.from_user.last_name or ''}"
        f"[{call.from_user.id}]: INLINE -> {call.data}"
    )
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
                await call.message.answer("❌ Не удалось получить расписание")
                return
            schedule = parse_schedule(html)
            text = format_schedule(schedule)
            await call.message.answer(text)
        else:
            await call.message.answer("Напиши из какой ты группы")
            await state.set_state(GroupForm.waiting_for_group)


@dp.message()
async def command_default(m: types.Message):
    await m.answer(f'I don\'t understand "{m.text}"\nMaybe try the help page at /help')


if __name__ == "__main__":
    import asyncio

    asyncio.run(dp.start_polling(bot))
