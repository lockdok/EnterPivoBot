"""Standalone migration script: backfills drinks_detail for existing drinks records."""
import asyncio
import logging
from bot.config import settings
from bot.database.db import Database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration")


async def main():
    logger.info(f"Connecting to database: {settings.database_path}")
    db = Database(settings.database_path)
    await db.init_db()

    current_version = await db.get_schema_version()
    logger.info(f"Current schema version: {current_version}")

    await db.run_migrations()

    new_version = await db.get_schema_version()
    logger.info(f"Migrations finished. New schema version: {new_version}")


if __name__ == "__main__":
    asyncio.run(main())

