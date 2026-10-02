from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bot.handlers import drink_parser


@pytest.mark.asyncio
async def test_auto_detection_disabled_ignores_regular_messages(monkeypatch):
    monkeypatch.setattr(drink_parser.settings, "auto_detect_drinks", False)
    message = SimpleNamespace(
        text="выпил 4 литра водки",
        from_user=SimpleNamespace(id=1),
    )
    db = AsyncMock()
    parse_message = Mock()
    monkeypatch.setattr(drink_parser, "parse_natural_drink_text", parse_message)

    await drink_parser.process_natural_text(message, db)

    parse_message.assert_not_called()
    db.add_drink.assert_not_awaited()


@pytest.mark.asyncio
async def test_drink_command_works_when_auto_detection_is_disabled(monkeypatch):
    monkeypatch.setattr(drink_parser.settings, "auto_detect_drinks", False)
    user = SimpleNamespace(id=1)
    db = AsyncMock()
    message = SimpleNamespace(
        text="/drink 500 5 пиво",
        from_user=user,
        chat=SimpleNamespace(id=-1001),
        reply=AsyncMock(),
    )
    record_drink = AsyncMock()
    monkeypatch.setattr(drink_parser, "record_and_notify_drink", record_drink)

    await drink_parser.cmd_drink(message, db)

    record_drink.assert_awaited_once_with(
        message=message,
        db=db,
        user=user,
        drink_name="пиво",
        volume_ml=500.0,
        abv=5.0,
    )