"""Database management module using aiosqlite."""
import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

# Current schema version. Bump this when adding new migrations.
CURRENT_SCHEMA_VERSION = 1


class Database:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path

    @asynccontextmanager
    async def _connect(self):
        """Open a connection with foreign key enforcement enabled."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            yield db

    async def init_db(self):
        """Initialize all database tables (idempotent)."""
        async with self._connect() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER,
                    chat_id INTEGER,
                    username TEXT,
                    full_name TEXT,
                    PRIMARY KEY (user_id, chat_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS drinks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    drink_name TEXT NOT NULL,
                    volume_ml REAL NOT NULL,
                    abv REAL NOT NULL,
                    vodka_equiv_ml REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS drinks_detail (
                    drink_id INTEGER PRIMARY KEY REFERENCES drinks(id) ON DELETE CASCADE,
                    category TEXT NOT NULL DEFAULT 'другое',
                    brand TEXT,
                    pure_alcohol_g REAL NOT NULL DEFAULT 0.0
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS monthly_winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    total_vodka_ml REAL NOT NULL,
                    announced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, year, month)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_settings (
                    chat_id INTEGER PRIMARY KEY,
                    roast_chance REAL DEFAULT 0.20,
                    timezone TEXT DEFAULT 'Europe/Moscow'
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indexes for fast leaderboard lookups
            await db.execute("CREATE INDEX IF NOT EXISTS idx_drinks_chat_created ON drinks(chat_id, created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_drinks_user_chat ON drinks(user_id, chat_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_detail_drink_id ON drinks_detail(drink_id)")

            await db.commit()

    # ------------------------------------------------------------------
    # Schema migrations
    # ------------------------------------------------------------------

    async def get_schema_version(self) -> int:
        """Return the highest applied schema version (0 if none)."""
        async with self._connect() as db:
            async with db.execute("SELECT MAX(version) FROM schema_version") as cur:
                row = await cur.fetchone()
                return row[0] if row and row[0] is not None else 0

    async def _set_schema_version(self, version: int):
        """Record that a migration version has been applied."""
        async with self._connect() as db:
            await db.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (version,)
            )
            await db.commit()

    async def run_migrations(self):
        """Apply any pending schema migrations and backfill data."""
        current = await self.get_schema_version()

        if current < 1:
            # Migration 1: backfill drinks_detail for pre-existing drinks records.
            # The drinks_detail table was created by init_db, but old rows in drinks
            # have no matching row in drinks_detail yet.
            await self._backfill_drinks_detail()
            await self._set_schema_version(1)

    async def _backfill_drinks_detail(self):
        """Fill drinks_detail for all existing drinks that have no detail row."""
        from bot.services.classifier import classify_drink, calculate_pure_alcohol_grams

        async with self._connect() as db:
            async with db.execute("""
                SELECT d.id, d.drink_name, d.volume_ml, d.abv
                FROM drinks d
                LEFT JOIN drinks_detail dd ON d.id = dd.drink_id
                WHERE dd.drink_id IS NULL
            """) as cur:
                rows = await cur.fetchall()

            for row in rows:
                drink_id, drink_name, volume_ml, abv = row
                category = classify_drink(drink_name, abv)
                pure_g = calculate_pure_alcohol_grams(volume_ml, abv)
                await db.execute(
                    "INSERT OR IGNORE INTO drinks_detail (drink_id, category, brand, pure_alcohol_g) VALUES (?, ?, ?, ?)",
                    (drink_id, category, drink_name, pure_g)
                )
            await db.commit()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def upsert_user(self, user_id: int, chat_id: int, username: Optional[str], full_name: str):
        """Insert or update user details in specific chat."""
        async with self._connect() as db:
            await db.execute("""
                INSERT INTO users (user_id, chat_id, username, full_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, chat_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name
            """, (user_id, chat_id, username, full_name))
            await db.commit()

    # ------------------------------------------------------------------
    # Drinks
    # ------------------------------------------------------------------

    async def add_drink(
        self,
        user_id: int,
        chat_id: int,
        drink_name: str,
        volume_ml: float,
        abv: float,
        vodka_equiv_ml: float
    ) -> int:
        """Record a drink entry and return its ID."""
        async with self._connect() as db:
            cursor = await db.execute("""
                INSERT INTO drinks (user_id, chat_id, drink_name, volume_ml, abv, vodka_equiv_ml)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, chat_id, drink_name, volume_ml, abv, vodka_equiv_ml))
            await db.commit()
            return cursor.lastrowid

    async def add_drink_detail(
        self,
        drink_id: int,
        category: str,
        brand: str,
        pure_alcohol_g: float
    ):
        """Insert detail record for a drink (1:1 with drinks table)."""
        async with self._connect() as db:
            await db.execute(
                "INSERT OR IGNORE INTO drinks_detail (drink_id, category, brand, pure_alcohol_g) VALUES (?, ?, ?, ?)",
                (drink_id, category, brand, pure_alcohol_g)
            )
            await db.commit()

    async def delete_last_drink(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """Remove the most recent drink entry for this user in this chat (undo).

        drinks_detail is removed automatically via ON DELETE CASCADE.
        """
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, drink_name, volume_ml, abv, vodka_equiv_ml, created_at
                FROM drinks
                WHERE user_id = ? AND chat_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (user_id, chat_id))
            row = await cursor.fetchone()
            if not row:
                return None

            drink_data = dict(row)
            await db.execute("DELETE FROM drinks WHERE id = ?", (drink_data["id"],))
            await db.commit()
            return drink_data

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_user_stats(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """Get vodka-equivalent consumption stats (today, week, month, all time)."""
        async with self._connect() as db:
            now = datetime.now()
            start_of_day = now.strftime("%Y-%m-%d 00:00:00")
            start_of_week = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")
            start_of_month = now.strftime("%Y-%m-01 00:00:00")

            async def fetch_sum(since_ts: Optional[str] = None):
                query = "SELECT COALESCE(SUM(vodka_equiv_ml), 0), COUNT(id) FROM drinks WHERE user_id = ? AND chat_id = ?"
                params = [user_id, chat_id]
                if since_ts:
                    query += " AND created_at >= ?"
                    params.append(since_ts)
                async with db.execute(query, params) as cur:
                    val, count = await cur.fetchone()
                    return round(val, 1), count

            today_vodka, today_count = await fetch_sum(start_of_day)
            week_vodka, week_count = await fetch_sum(start_of_week)
            month_vodka, month_count = await fetch_sum(start_of_month)
            total_vodka, total_count = await fetch_sum(None)

            return {
                "today_vodka": today_vodka,
                "today_count": today_count,
                "week_vodka": week_vodka,
                "week_count": week_count,
                "month_vodka": month_vodka,
                "month_count": month_count,
                "total_vodka": total_vodka,
                "total_count": total_count,
            }

    async def get_user_category_stats(
        self,
        user_id: int,
        chat_id: int,
        since: Optional[datetime] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Return per-category breakdown: total ml, total grams of pure alcohol, count.

        Only counts drinks that have a matching drinks_detail row.
        """
        async with self._connect() as db:
            query = """
                SELECT
                    dd.category,
                    ROUND(SUM(d.volume_ml), 1)      AS total_ml,
                    ROUND(SUM(dd.pure_alcohol_g), 1) AS total_g,
                    COUNT(d.id)                      AS cnt
                FROM drinks d
                JOIN drinks_detail dd ON d.id = dd.drink_id
                WHERE d.user_id = ? AND d.chat_id = ?
            """
            params: List[Any] = [user_id, chat_id]
            if since:
                query += " AND d.created_at >= ?"
                params.append(since.strftime("%Y-%m-%d %H:%M:%S"))
            query += " GROUP BY dd.category ORDER BY total_ml DESC"

            async with db.execute(query, params) as cur:
                rows = await cur.fetchall()

            return {
                row[0]: {"total_ml": row[1], "total_g": row[2], "count": row[3]}
                for row in rows
            }

    async def get_user_drink_history(
        self,
        user_id: int,
        chat_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Return last N drink records with detail info for a user in a chat."""
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT
                    d.id,
                    d.drink_name,
                    d.volume_ml,
                    d.abv,
                    d.vodka_equiv_ml,
                    d.created_at,
                    COALESCE(dd.category, 'другое') AS category,
                    COALESCE(dd.pure_alcohol_g, 0)  AS pure_alcohol_g
                FROM drinks d
                LEFT JOIN drinks_detail dd ON d.id = dd.drink_id
                WHERE d.user_id = ? AND d.chat_id = ?
                ORDER BY d.id DESC
                LIMIT ?
            """, (user_id, chat_id, limit)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Leaderboard (vodka equiv only — used for Top/Rankings)
    # ------------------------------------------------------------------

    async def get_leaderboard(
        self,
        chat_id: int,
        since_datetime: Optional[datetime] = None,
        until_datetime: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top drinkers in chat ordered by vodka equivalent (unchanged)."""
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT
                    d.user_id,
                    COALESCE(u.username, '') as username,
                    COALESCE(u.full_name, 'Анонимный алконавт') as full_name,
                    ROUND(SUM(d.vodka_equiv_ml), 1) as total_vodka,
                    COUNT(d.id) as drinks_count
                FROM drinks d
                LEFT JOIN users u ON d.user_id = u.user_id AND d.chat_id = u.chat_id
                WHERE d.chat_id = ?
            """
            params: List[Any] = [chat_id]

            if since_datetime:
                query += " AND d.created_at >= ?"
                params.append(since_datetime.strftime("%Y-%m-%d %H:%M:%S"))

            if until_datetime:
                query += " AND d.created_at <= ?"
                params.append(until_datetime.strftime("%Y-%m-%d %H:%M:%S"))

            query += """
                GROUP BY d.user_id
                ORDER BY total_vodka DESC
                LIMIT ?
            """
            params.append(limit)

            async with db.execute(query, params) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_all_active_chat_ids(self) -> List[int]:
        """Fetch distinct chat IDs that have users or drink records."""
        async with self._connect() as db:
            async with db.execute("""
                SELECT DISTINCT chat_id FROM users
                UNION
                SELECT DISTINCT chat_id FROM drinks
            """) as cur:
                rows = await cur.fetchall()
                return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Monthly winners
    # ------------------------------------------------------------------

    async def set_monthly_winner(
        self,
        chat_id: int,
        year: int,
        month: int,
        user_id: int,
        total_vodka_ml: float
    ):
        """Save official monthly winner into database."""
        async with self._connect() as db:
            await db.execute("""
                INSERT INTO monthly_winners (chat_id, year, month, user_id, total_vodka_ml)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, year, month) DO UPDATE SET
                    user_id = excluded.user_id,
                    total_vodka_ml = excluded.total_vodka_ml,
                    announced_at = CURRENT_TIMESTAMP
            """, (chat_id, year, month, user_id, total_vodka_ml))
            await db.commit()

    async def get_active_monthly_winner(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get the winner of the PREVIOUS calendar month (subject to roasting)."""
        now = datetime.now()
        first_of_curr_month = now.replace(day=1)
        prev_month_date = first_of_curr_month - timedelta(days=1)
        prev_year = prev_month_date.year
        prev_month = prev_month_date.month

        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT
                    w.user_id,
                    w.year,
                    w.month,
                    w.total_vodka_ml,
                    COALESCE(u.username, '') as username,
                    COALESCE(u.full_name, 'Чемпион') as full_name
                FROM monthly_winners w
                LEFT JOIN users u ON w.user_id = u.user_id AND w.chat_id = u.chat_id
                WHERE w.chat_id = ? AND w.year = ? AND w.month = ?
                LIMIT 1
            """, (chat_id, prev_year, prev_month)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None
