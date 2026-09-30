"""Common commands handler: /start, /help."""
from aiogram import Router, types
from aiogram.filters import Command
from bot.database.db import Database

router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: types.Message, db: Database):
    """Handle /start command."""
    if message.from_user:
        await db.upsert_user(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )

    text = (
        "🍻 **Добро пожаловать в EnterPivoBot!** 🍻\n\n"
        "Я слежу за количеством выпитого алкоголя в этом чате и перевожу всё в честный **водочный эквивалент** (исходя из 40% водки).\n\n"
        "📅 **Каждое воскресенье в 23:00** — объявление недельного топа.\n"
        "👑 **1-го числа каждого месяца** — объявление Чемпиона Месяца.\n"
        "⚡️ **Особое правило**: Весь следующий месяц бот будет публично подкалывать и унижать победителя за его алкогольные подвиги!\n\n"
        "Напишите /help, чтобы увидеть список команд и примеры сообщений."
    )
    await message.reply(text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command."""
    text = (
        "📖 **Как пользоваться EnterPivoBot:**\n\n"
        "1️⃣ **Просто пишите в чат свободным текстом:**\n"
        "• *«выпил 0.5 пива»*\n"
        "• *«накатил 100 водки»*\n"
        "• *«бахнул бокал вина»*\n"
        "• *«махнул рюмку коньяка»*\n"
        "• *«хлопнул 2 банки пива 6%»*\n"
        "Если данных не хватит, я сам вежливо (или с сарказмом) уточню объём или градус через удобные кнопки!\n\n"
        "2️⃣ **Быстрые команды:**\n"
        "• `/drink [объем мл] [градус] [название]` — быстрый точный ввод (например: `/drink 500 5 пиво`)\n"
        "• `/stats` или `/стата` — ваша личная статистика выпитого\n"
        "• `/top` или `/топ` — рейтинг лидеров чата (неделя / месяц)\n"
        "• `/winner` или `/чемпион` — текущий алкоголик месяца, находящийся на доске позора\n"
        "• `/cancel` или `/отмена` — удалить последнюю ошибочно внесенную запись\n\n"
        "📐 **Формула водочного эквивалента:**\n"
        "$$\\text{Водка (мл)} = \\text{Объем (мл)} \\times \\frac{\\text{Крепость}\\%}{40\\%}$$\n"
        "Например: 500 мл пива 5% = 62.5 мл водки."
    )
    await message.reply(text, parse_mode="Markdown")

