from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers import common


@pytest.mark.asyncio
async def test_settings_command_shows_toggle_to_chat_admin():
    user = SimpleNamespace(id=10, username="chat_admin")
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-1001),
        from_user=user,
        reply=AsyncMock(),
    )
    bot = AsyncMock()
    bot.get_chat_member.return_value = SimpleNamespace(status="administrator")
    db = AsyncMock()
    db.get_auto_detect_drinks.return_value = True

    await common.cmd_settings(message, db, bot)

    bot.get_chat_member.assert_awaited_once_with(-1001, user.id)
    reply = message.reply.call_args
    assert "включено" in reply.args[0]
    assert reply.kwargs["reply_markup"].inline_keyboard[0][0].callback_data == common.SETTINGS_CALLBACK


@pytest.mark.asyncio
async def test_settings_command_rejects_regular_member():
    user = SimpleNamespace(id=10, username="member")
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-1001),
        from_user=user,
        reply=AsyncMock(),
    )
    bot = AsyncMock()
    bot.get_chat_member.return_value = SimpleNamespace(status="member")
    db = AsyncMock()

    await common.cmd_settings(message, db, bot)

    db.get_auto_detect_drinks.assert_not_awaited()
    assert "только администраторы" in message.reply.call_args.args[0].lower()


@pytest.mark.asyncio
async def test_owner_can_open_settings_without_chat_admin_status():
    user = SimpleNamespace(id=10, username="lockdok")
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-1001),
        from_user=user,
        reply=AsyncMock(),
    )
    bot = AsyncMock()
    db = AsyncMock()
    db.get_auto_detect_drinks.return_value = False

    await common.cmd_settings(message, db, bot)

    bot.get_chat_member.assert_not_awaited()
    db.get_auto_detect_drinks.assert_awaited_once()