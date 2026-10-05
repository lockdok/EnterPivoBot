"""Stats and Leaderboard handlers."""
import html
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command
from bot.database.db import Database
from bot.services.classifier import get_category_emoji
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

    status_badge = "🏆😵‍💫 <b>[ОФИЦИАЛЬНЫЙ АЛКОБАРОН МЕСЯЦА]</b>\n" if is_winner else ""

    text = (
        f'📊 <b>Личное дело алконавта <a href="tg://user?id={user_id}">'
        f"{html.escape(message.from_user.full_name)}</a>:</b>\n"
        f"{status_badge}\n"
        f"• <b>Сегодня</b>: {stats['today_vodka']} мл водки ({stats['today_count']} раз)\n"
        f"• <b>На этой неделе</b>: {stats['week_vodka']} мл водки ({stats['week_count']} раз)\n"
        f"• <b>В этом месяце</b>: {stats['month_vodka']} мл водки ({stats['month_count']} раз)\n"
        f"• <b>За всё время</b>: {stats['total_vodka']} мл водки ({stats['total_count']} раз)\n\n"
    )

    if stats["total_vodka"] == 0:
        text += "🕊 Вы ещё ни разу не залогировали выпивку. Святой человек (или шпион)!"
    elif stats["today_vodka"] > 250:
        text += "⚠️ Ого, более стакана чистой водки за сегодня! Рекомендуем выпить воды и поспать."
    elif stats["week_vodka"] > 1000:
        text += "🔥 Литр водки за неделю! Вы уверенно идёте на титул чемпиона месяца."
    else:
        text += "👌 Показатели в пределах нормы (по меркам нашего бара)."

    await message.reply(text, parse_mode="HTML")


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


@router.message(Command("mystats", "моястата"))
async def cmd_mystats(message: types.Message, db: Database):
    """Show detailed personal statistics by drink categories and recent history."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = html.escape(message.from_user.full_name)

    cat_stats = await db.get_user_category_stats(user_id, chat_id)
    history = await db.get_user_drink_history(user_id, chat_id, limit=10)

    if not cat_stats and not history:
        await message.reply(
            f"📊 <b>Детальная статистика: {user_name}</b>\n\n"
            f"🕊 Вы ещё ничего не записали в этом чате. Полная трезвость!",
            parse_mode="HTML"
        )
        return

    total_drinks = sum(item["count"] for item in cat_stats.values())
    total_pure_alcohol = sum(item["total_g"] for item in cat_stats.values())

    lines = [
        f"📊 <b>Детальная статистика: {user_name}</b>",
        f"Всего подходов: <b>{total_drinks}</b> | Чистый спирт: <b>{total_pure_alcohol:.1f} г</b>\n",
        "<b>Разбивка по категориям:</b>"
    ]

    for cat_name, data in cat_stats.items():
        emoji = get_category_emoji(cat_name)
        title = cat_name.capitalize()
        lines.append(
            f"{emoji} <b>{title}</b>: {data['total_ml']:.0f} мл | "
            f"<b>{data['total_g']:.1f} г</b> спирта ({data['count']} раз)"
        )

    if history:
        lines.append("\n📋 <b>Последние 10 записей:</b>")
        for item in history:
            emoji = get_category_emoji(item['category'])
            name = html.escape(item['drink_name'])
            dt_str = item.get("created_at") or ""
            if dt_str and len(dt_str) >= 16:
                date_part, time_part = dt_str[:10], dt_str[11:16]
                d_parts = date_part.split("-")
                if len(d_parts) == 3:
                    dt_str = f"{d_parts[2]}.{d_parts[1]} {time_part}"
            lines.append(
                f"• {dt_str} — {emoji} <b>{name}</b> {item['volume_ml']:.0f} мл "
                f"({item['abv']:.1f}%) — {item['pure_alcohol_g']:.1f} г спирта"
            )

    full_text = "\n".join(lines)
    await message.reply(full_text, parse_mode="HTML")
