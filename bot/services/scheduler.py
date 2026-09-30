"""Scheduler service for automated weekly and monthly reports."""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from bot.database.db import Database

logger = logging.getLogger(__name__)


def format_leaderboard_message(leaderboard: list, title: str) -> str:
    """Format a list of top drinkers into a readable Markdown message."""
    if not leaderboard:
        return f"{title}\n\n🕸 В этом периоде никто не пил... Либо все шифруются, либо пора вызывать врачей!"

    lines = [f"📊 **{title}**\n"]
    medals = ["🥇", "🥈", "🥉"]

    for idx, row in enumerate(leaderboard, start=1):
        medal = medals[idx - 1] if idx <= 3 else f"{idx}."
        user_name = f"@{row['username']}" if row['username'] else row['full_name']
        vodka_ml = row['total_vodka']
        drinks_count = row['drinks_count']
        lines.append(f"{medal} **{user_name}** — **{vodka_ml} мл** водки ({drinks_count} подходов)")

    return "\n".join(lines)


async def send_weekly_reports(bot: Bot, db: Database):
    """Publish weekly leaderboards to all active groups."""
    logger.info("Executing weekly leaderboard reporting...")
    now = datetime.now()
    start_of_week = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second)
    
    chat_ids = await db.get_all_active_chat_ids()
    for chat_id in chat_ids:
        # Only send to groups / supergroups (negative chat IDs)
        if chat_id > 0:
            continue
        try:
            top_list = await db.get_leaderboard(chat_id, since_datetime=start_of_week, limit=10)
            text = format_leaderboard_message(top_list, "🏆 ИТОГИ НЕДЕЛИ: АЛКО-РЕЙТИНГ")
            text += "\n\n💡 Недельный рейтинг обновлён. Новый забег начинается прямо сейчас!"
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send weekly report to chat {chat_id}: {e}")


async def announce_monthly_winner(bot: Bot, db: Database):
    """Determine and crown the previous month's winner and notify the chat."""
    logger.info("Executing monthly winner announcement...")
    now = datetime.now()
    
    # Calculate previous month date range
    first_of_curr_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_of_prev_month = first_of_curr_month - timedelta(seconds=1)
    first_of_prev_month = last_of_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    prev_year = first_of_prev_month.year
    prev_month = first_of_prev_month.month

    month_names = [
        "", "январе", "феврале", "марте", "апреле", "мае", "июне",
        "июле", "августе", "сентябре", "октябре", "ноябре", "декабре"
    ]
    month_name = month_names[prev_month]

    chat_ids = await db.get_all_active_chat_ids()
    for chat_id in chat_ids:
        if chat_id > 0:
            continue
        try:
            top_list = await db.get_leaderboard(
                chat_id,
                since_datetime=first_of_prev_month,
                until_datetime=last_of_prev_month,
                limit=1
            )
            if not top_list or top_list[0]["total_vodka"] <= 0:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"👑 **Итоги месяца ({month_name} {prev_year})**:\n\nНикто не выпил достаточно для титула чемпиона. Скучно живёте!",
                    parse_mode="Markdown"
                )
                continue

            winner = top_list[0]
            winner_user_id = winner["user_id"]
            winner_total_vodka = winner["total_vodka"]
            winner_name = f"@{winner['username']}" if winner['username'] else winner['full_name']

            # Save to monthly_winners table
            await db.set_monthly_winner(
                chat_id=chat_id,
                year=prev_year,
                month=prev_month,
                user_id=winner_user_id,
                total_vodka_ml=winner_total_vodka
            )

            announcement = (
                f"🚨 **ВНИМАНИЕ ВСЕМ УЧАСТНИКАМ ЧАТА!** 🚨\n\n"
                f"Подведены официальные итоги за **{month_name} {prev_year} года**!\n\n"
                f"🏆 Абсолютным и безоговорочным **АЛКОБАРОНОМ МЕСЯЦА** становится:\n"
                f"👉 **{winner_name}** 👈\n\n"
                f"🩸 Личный рекорд: **{winner_total_vodka} мл** в водочном эквиваленте!\n\n"
                f"⚠️ **Внимание победителю:** В течение всего наступившего месяца бот будет пристально "
                f"следить за каждым твоим сообщением и регулярно напоминать тебе о твоём почётном диагнозе. Пощады не жди!"
            )

            await bot.send_message(chat_id=chat_id, text=announcement, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to announce monthly winner to chat {chat_id}: {e}")


def setup_scheduler(bot: Bot, db: Database, timezone: str = "Europe/Moscow") -> AsyncIOScheduler:
    """Configure and return the AsyncIOScheduler instance."""
    scheduler = AsyncIOScheduler(timezone=timezone)

    # Weekly report: Every Sunday at 23:00
    scheduler.add_job(
        send_weekly_reports,
        trigger=CronTrigger(day_of_week="sun", hour=23, minute=0, timezone=timezone),
        args=[bot, db],
        id="weekly_reports",
        replace_existing=True
    )

    # Monthly winner announcement: 1st of every month at 00:01
    scheduler.add_job(
        announce_monthly_winner,
        trigger=CronTrigger(day=1, hour=0, minute=1, timezone=timezone),
        args=[bot, db],
        id="monthly_winner_announcement",
        replace_existing=True
    )

    return scheduler

