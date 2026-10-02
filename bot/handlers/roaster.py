"""Roaster handler for mocking the monthly winner."""
import random
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from bot.database.db import Database
from bot.services.phrases import get_random_winner_roast
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router(name="roaster")


@router.message(Command("roast", "подкол"))
@router.message(F.text.casefold().in_({"подкол", "роаст"}))
async def cmd_manual_roast(message: types.Message, db: Database):
    """Manually test a roast for the active monthly winner or the caller."""
    active_winner = await db.get_active_monthly_winner(message.chat.id)
    target_name = None
    if active_winner:
        target_name = f"@{active_winner['username']}" if active_winner['username'] else active_winner['full_name']
    elif message.from_user:
        target_name = message.from_user.full_name

    roast = get_random_winner_roast(target_name)
    await message.reply(f"🎯 {roast}")


@router.message()
async def check_and_roast_winner(message: types.Message, db: Database):
    """
    Check if the message author is the active monthly winner and roast with probability.
    """
    # Only active in group chats
    if message.chat.type not in ["group", "supergroup"]:
        return

    if not message.from_user or message.from_user.is_bot:
        return

    # Check if this user is the active monthly champion
    active_winner = await db.get_active_monthly_winner(message.chat.id)
    if not active_winner or active_winner.get("user_id") != message.from_user.id:
        return

    # Probability check
    if random.random() <= settings.roast_probability:
        user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        roast = get_random_winner_roast(user_name)
        try:
            await message.reply(f"💀 {roast}")
        except Exception as e:
            logger.error(f"Error sending roast reply: {e}")

