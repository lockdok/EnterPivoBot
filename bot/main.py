"""Entry point for EnterPivoBot."""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

from bot.config import settings
from bot.database.db import Database
from bot.handlers import (
    common_router,
    stats_router,
    drink_parser_router,
    roaster_router
)
from bot.services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("EnterPivoBot")

BOT_COMMANDS = [
    BotCommand(command="drink",    description="Записать выпитое: /drink 500 5 пиво"),
    BotCommand(command="stats",    description="Личная статистика в водочном эквиваленте"),
    BotCommand(command="mystats",  description="Детальная статистика по типам напитков"),
    BotCommand(command="top",      description="Топ-5 чата за неделю и месяц"),
    BotCommand(command="winner",   description="Действующий алкобарон месяца"),
    BotCommand(command="cancel",   description="Отменить последнюю запись"),
    BotCommand(command="help",     description="Как пользоваться ботом"),
]


async def main():
    if not settings.bot_token or settings.bot_token == "CHANGE_ME":
        logger.error(
            "BOT_TOKEN is not configured! Please provide your Telegram bot token in the .env file."
        )
        return

    logger.info("Initializing EnterPivoBot...")

    # Initialize Database
    db = Database(settings.database_path)
    await db.init_db()
    logger.info(f"Database initialized at {settings.database_path}")

    # Apply pending schema migrations (safe to run every startup)
    await db.run_migrations()
    logger.info("Schema migrations applied.")

    # Initialize Bot & Dispatcher (no global parse_mode — set it per-message explicitly)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties()
    )
    dp = Dispatcher()

    # Provide db instance to all handlers
    dp["db"] = db

    # Register routers in priority order
    dp.include_router(common_router)
    dp.include_router(stats_router)
    dp.include_router(drink_parser_router)
    dp.include_router(roaster_router)

    # Register bot commands so they appear in the Telegram menu
    try:
        await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())
        await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllGroupChats())
        await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        logger.info("Bot commands registered in Telegram menu (default, groups, private).")
    except Exception as e:
        logger.warning(f"Failed to register bot commands: {e}")

    # Initialize Scheduler
    scheduler = setup_scheduler(bot=bot, db=db, timezone=settings.timezone)
    scheduler.start()
    logger.info(f"Scheduler started with timezone: {settings.timezone}")

    try:
        logger.info("Starting bot polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down scheduler and bot session...")
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
