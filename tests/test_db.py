import os
import pytest
import pytest_asyncio
from bot.database.db import Database

TEST_DB_PATH = "test_bot_temp.db"


@pytest_asyncio.fixture
async def temp_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
    db = Database(TEST_DB_PATH)
    await db.init_db()
    yield db
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_upsert_user_and_add_drink(temp_db):
    await temp_db.upsert_user(101, -1001, "alcotest", "Alco Tester")
    
    # Add 500ml beer 5% -> 62.5ml vodka
    drink_id = await temp_db.add_drink(
        user_id=101,
        chat_id=-1001,
        drink_name="пиво",
        volume_ml=500.0,
        abv=5.0,
        vodka_equiv_ml=62.5
    )
    assert drink_id > 0

    stats = await temp_db.get_user_stats(101, -1001)
    assert stats["today_vodka"] == 62.5
    assert stats["today_count"] == 1
    assert stats["total_vodka"] == 62.5


@pytest.mark.asyncio
async def test_leaderboard(temp_db):
    await temp_db.upsert_user(1, -1001, "drinker1", "Ivan")
    await temp_db.upsert_user(2, -1001, "drinker2", "Petr")

    # Ivan: 100ml vodka
    await temp_db.add_drink(1, -1001, "водка", 100.0, 40.0, 100.0)
    # Petr: 500ml beer (62.5) + 500ml beer (62.5) = 125.0
    await temp_db.add_drink(2, -1001, "пиво", 500.0, 5.0, 62.5)
    await temp_db.add_drink(2, -1001, "пиво", 500.0, 5.0, 62.5)

    leaderboard = await temp_db.get_leaderboard(-1001)
    assert len(leaderboard) == 2
    # Petr is first with 125ml
    assert leaderboard[0]["user_id"] == 2
    assert leaderboard[0]["total_vodka"] == 125.0
    # Ivan is second with 100ml
    assert leaderboard[1]["user_id"] == 1
    assert leaderboard[1]["total_vodka"] == 100.0


@pytest.mark.asyncio
async def test_delete_last_drink(temp_db):
    await temp_db.add_drink(1, -1001, "водка", 100.0, 40.0, 100.0)
    deleted = await temp_db.delete_last_drink(1, -1001)
    assert deleted is not None
    assert deleted["drink_name"] == "водка"

    stats = await temp_db.get_user_stats(1, -1001)
    assert stats["total_vodka"] == 0.0


@pytest.mark.asyncio
async def test_monthly_winner_storage_and_active_retrieval(temp_db):
    from datetime import datetime, timedelta
    now = datetime.now()
    prev_month_date = now.replace(day=1) - timedelta(days=1)
    prev_year = prev_month_date.year
    prev_month = prev_month_date.month

    await temp_db.upsert_user(777, -1001, "champ", "Super Drinker")
    await temp_db.set_monthly_winner(-1001, prev_year, prev_month, 777, 3500.0)

    active_winner = await temp_db.get_active_monthly_winner(-1001)
    assert active_winner is not None
    assert active_winner["user_id"] == 777
    assert active_winner["total_vodka_ml"] == 3500.0

