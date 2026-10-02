"""Common commands handler: /start, /help."""
import logging
from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from bot.config import settings
from bot.database.db import Database

router = Router(name="common")
logger = logging.getLogger(__name__)

SETTINGS_CALLBACK = "settings:auto-detect"


def _settings_text(enabled: bool) -> str:
    state = "включено" if enabled else "выключено"
    return (
        "⚙️ **Настройки этого чата**\n\n"
        f"Автораспознавание сообщений: **{state}**.\n"
        "Команда `/drink` работает независимо от этой настройки."
    )


def _settings_keyboard(enabled: bool) -> types.InlineKeyboardMarkup:
    action = "Выключить" if enabled else "Включить"
    return types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(
            text=f"{action} автораспознавание",
            callback_data=SETTINGS_CALLBACK
        )
    ]])


async def _can_manage_settings(bot: Bot, chat_id: int, user: types.User) -> bool:
    if (user.username or "").casefold() == "lockdok":
        return True
    if chat_id > 0:
        return False

    try:
        member = await bot.get_chat_member(chat_id, user.id)
    except TelegramAPIError:
        logger.exception("Failed to check settings permissions in chat %s", chat_id)
        return False
    return member.status in {"administrator", "creator"}


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
        "1️⃣ **Автораспознавание сообщений:**\n"
        "По умолчанию выключено. Администраторы чата и владелец @lockdok могут включить его через `/settings`.\n"
        "• *«выпил 0.5 пива»*\n"
        "• *«накатил 100 водки»*\n"
        "• *«бахнул бокал вина»*\n"
        "• *«махнул рюмку коньяка»*\n"
        "• *«хлопнул 2 банки пива 6%»*\n"
        "Если данных не хватит, я уточню объём или градус через кнопки. Команда `/drink` работает и при выключенном автораспознавании.\n\n"
        "2️⃣ **Быстрые команды:**\n"
        "• `/drink [объем мл] [градус] [название]` — быстрый точный ввод (например: `/drink 500 5 пиво`)\n"
        "• `/settings` — включить или выключить автораспознавание в этом чате (для администраторов и @lockdok)\n"
        "• `/stats` или `/стата` — ваша личная статистика в водочном эквиваленте\n"
        "• `/mystats` или `/моястата` — детальная статистика по категориям (пиво, вино, крепкий) и граммам чистого спирта\n"
        "• `/top` или `/топ` — рейтинг лидеров чата (неделя / месяц)\n"
        "• `/winner` или `/чемпион` — текущий алкоголик месяца, находящийся на доске позора\n"
        "• `/cancel` или `/отмена` — удалить последнюю ошибочно внесенную запись\n\n"
        "📐 **Формула водочного эквивалента:**\n"
        "$$\\text{Водка (мл)} = \\text{Объем (мл)} \\times \\frac{\\text{Крепость}\\%}{40\\%}$$\n"
        "Например: 500 мл пива 5% = 62.5 мл водки."
    )
    await message.reply(text, parse_mode="Markdown")


@router.message(Command("settings"))
async def cmd_settings(message: types.Message, db: Database, bot: Bot):
    """Show drink auto-detection settings for this chat."""
    if not message.from_user:
        return
    if not await _can_manage_settings(bot, message.chat.id, message.from_user):
        await message.reply("Настройки могут менять только администраторы чата и владелец @lockdok.")
        return

    enabled = await db.get_auto_detect_drinks(
        message.chat.id,
        default=settings.auto_detect_drinks
    )
    await message.reply(
        _settings_text(enabled),
        reply_markup=_settings_keyboard(enabled),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == SETTINGS_CALLBACK)
async def callback_toggle_auto_detection(callback: types.CallbackQuery, db: Database, bot: Bot):
    """Toggle chat auto-detection after rechecking the caller's permissions."""
    message = callback.message
    if not callback.from_user or not isinstance(message, types.Message):
        await callback.answer("Не удалось открыть настройки этого чата.", show_alert=True)
        return
    if not await _can_manage_settings(bot, message.chat.id, callback.from_user):
        await callback.answer("Только администраторы чата и @lockdok могут менять настройку.", show_alert=True)
        return

    enabled = await db.toggle_auto_detect_drinks(
        message.chat.id,
        default=settings.auto_detect_drinks
    )
    await message.edit_text(
        _settings_text(enabled),
        reply_markup=_settings_keyboard(enabled),
        parse_mode="Markdown"
    )
    await callback.answer("Настройка сохранена")

