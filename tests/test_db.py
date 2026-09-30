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


@pytest.mark.asyncio
async def test_drink_detail_and_cascade_delete(temp_db):
    user_id = 55
    chat_id = -1001

    drink_id = await temp_db.add_drink(
        user_id=user_id,
        chat_id=chat_id,
        drink_name="Пиво Светлое",
        volume_ml=500.0,
        abv=5.0,
        vodka_equiv_ml=62.5
    )
    await temp_db.add_drink_detail(
        drink_id=drink_id,
        category="пиво",
        brand="Пиво Светлое",
        pure_alcohol_g=19.72
    )

    # Check category stats
    cat_stats = await temp_db.get_user_category_stats(user_id, chat_id)
    assert "пиво" in cat_stats
    assert cat_stats["пиво"]["total_ml"] == 500.0
    assert cat_stats["пиво"]["total_g"] == 19.7
    assert cat_stats["пиво"]["count"] == 1

    # Check history
    history = await temp_db.get_user_drink_history(user_id, chat_id, limit=5)
    assert len(history) == 1
    assert history[0]["category"] == "пиво"
    assert history[0]["pure_alcohol_g"] == 19.72

    # Cascade delete via delete_last_drink
    deleted = await temp_db.delete_last_drink(user_id, chat_id)
    assert deleted is not None
    assert deleted["id"] == drink_id

    # Verify drinks_detail was cascade deleted
    async with temp_db._connect() as db:
        async with db.execute("SELECT COUNT(*) FROM drinks_detail WHERE drink_id = ?", (drink_id,)) as cur:
            row = await cur.fetchone()
            assert row[0] == 0

    # Stats should now be empty
    cat_stats_after = await temp_db.get_user_category_stats(user_id, chat_id)
    assert len(cat_stats_after) == 0


@pytest.mark.asyncio
async def test_migrations_and_backfill(temp_db):
    # Insert legacy drinks row directly without details
    async with temp_db._connect() as db:
        cur = await db.execute(
            "INSERT INTO drinks (user_id, chat_id, drink_name, volume_ml, abv, vodka_equiv_ml) VALUES (?, ?, ?, ?, ?, ?)",
            (99, -1001, "Шампанское Абрау", 750.0, 12.0, 225.0)
        )
        await db.commit()
        legacy_id = cur.lastrowid

    # Reset schema version to 0 to simulate pre-migration state
    async with temp_db._connect() as db:
        await db.execute("DELETE FROM schema_version")
        await db.commit()

    # Run migrations
    await temp_db.run_migrations()

    # Schema version should be at least 1
    ver = await temp_db.get_schema_version()
    assert ver >= 1

    # drinks_detail should now be populated for the legacy record
    history = await temp_db.get_user_drink_history(99, -1001)
    assert len(history) == 1
    assert history[0]["category"] == "вино"
    assert history[0]["pure_alcohol_g"] > 0


