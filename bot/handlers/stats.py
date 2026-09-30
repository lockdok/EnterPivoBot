"""Stats and Leaderboard handlers."""
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command
from bot.database.db import Database
from bot.services.scheduler import format_leaderboard_message

router = Router(name="stats")


@router.message(Command("stats", "стата"))
async def cmd_stats(message: types.Message, db: Database):
    """Show personal statistics for the caller."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    stats = await db.get_user_stats(user_id, chat_id)
    active_winner = await db.get_active_monthly_winner(chat_id)
    is_winner = bool(active_winner and active_winner.get("user_id") == user_id)

    status_badge = "🏆😵‍💫 **[ОФИЦИАЛЬНЫЙ АЛКОБАРОН МЕСЯЦА]**\n" if is_winner else ""

    text = (
        f"📊 **Личное дело алконавта {message.from_user.mention_markdown(message.from_user.full_name)}:**\n"
        f"{status_badge}\n"
        f"• **Сегодня**: {stats['today_vodka']} мл водки ({stats['today_count']} раз)\n"
        f"• **На этой неделе**: {stats['week_vodka']} мл водки ({stats['week_count']} раз)\n"
        f"• **В этом месяце**: {stats['month_vodka']} мл водки ({stats['month_count']} раз)\n"
        f"• **За всё время**: {stats['total_vodka']} мл водки ({stats['total_count']} раз)\n\n"
    )

    if stats["total_vodka"] == 0:
        text += "🕊 Вы ещё ни разу не залогировали выпивку. Святой человек (или шпион)!"
    elif stats["today_vodka"] > 250:
        text += "⚠️ Ого, более стакана чистой водки за сегодня! Рекомендуем выпить воды и поспать."
    elif stats["week_vodka"] > 1000:
        text += "🔥 Литр водки за неделю! Вы уверенно идёте на титул чемпиона месяца."
    else:
        text += "👌 Показатели в пределах нормы (по меркам нашего бара)."

    await message.reply(text, parse_mode="Markdown")


@router.message(Command("top", "топ"))
async def cmd_top(message: types.Message, db: Database):
    """Show chat top leaderboards for week and month."""
    chat_id = message.chat.id
    now = datetime.now()

    # Current week
    start_of_week = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second)
    week_top = await db.get_leaderboard(chat_id, since_datetime=start_of_week, limit=5)

    # Current month
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_top = await db.get_leaderboard(chat_id, since_datetime=start_of_month, limit=5)

    text_week = format_leaderboard_message(week_top, "🏆 ТОП-5 НА ЭТОЙ НЕДЕЛЕ")
    text_month = format_leaderboard_message(month_top, "👑 ТОП-5 В ЭТОМ МЕСЯЦЕ")

    full_text = f"{text_week}\n\n{'—' * 20}\n\n{text_month}"
    await message.reply(full_text, parse_mode="HTML")


@router.message(Command("winner", "чемпион", "победитель"))
async def cmd_winner(message: types.Message, db: Database):
    """Show current active monthly winner subject to roast."""
    chat_id = message.chat.id
    winner = await db.get_active_monthly_winner(chat_id)

    if not winner:
        await message.reply(
            "🕊 В текущем месяце у нас пока нет официального чемпиона прошлого месяца. Все трезвенники (или данные ещё не подведены)!",
            parse_mode="Markdown"
        )
        return

    name = f"@{winner['username']}" if winner['username'] else winner['full_name']
    text = (
        f"👑 **ДОСКА ПОЗОРА: ДЕЙСТВУЮЩИЙ ЧЕМПИОН МЕСЯЦА**\n\n"
        f"Главный алко-герой: **{name}**\n"
        f"Зафиксированный рекорд: **{winner['total_vodka_ml']} мл** водки!\n\n"
        f"🎯 Напоминаем: в течение всего месяца бот оставляет за собой законное право "
        f"язвительно комментировать его сообщения в этом чате. Уважайте старших по градусу!"
    )
    await message.reply(text, parse_mode="Markdown")

