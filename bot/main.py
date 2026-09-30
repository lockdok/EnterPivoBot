"""Entry point for EnterPivoBot."""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

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

    # Initialize Bot & Dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Provide db instance to all handlers
    dp["db"] = db

    # Register routers in priority order
    dp.include_router(common_router)
    dp.include_router(stats_router)
    dp.include_router(drink_parser_router)
    dp.include_router(roaster_router)

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

