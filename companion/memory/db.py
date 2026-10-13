from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = Path("data/companion.db")


def to_utc_iso(dt: datetime) -> str:
    """One fixed UTC format so string comparison in SQL matches time order."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Database:
    def __init__(self, path: Path = DEFAULT_DB_PATH) -> None:
        self.path = Path(path)
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    async def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        async with self._conn.execute(sql, params) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def _run(self, sql: str, params: tuple = ()) -> int:
        async with self._conn.execute(sql, params) as cur:
            await self._conn.commit()
            return cur.lastrowid

    # ---- settings ----
    async def get_settings(self) -> dict[str, str]:
        rows = await self._all("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in rows}

    async def set_setting(self, key: str, value: str) -> None:
        await self._run(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE
               SET value = excluded.value, updated_at = datetime('now')""",
            (key, value),
        )

    # ---- facts (knowledge graph triples) ----
    async def add_fact(self, subject: str, relation: str, obj: str,
                       source: str = "user_stated") -> None:
        await self._run(
            "INSERT OR IGNORE INTO facts (subject, relation, object, source) VALUES (?,?,?,?)",
            (subject, relation, obj, source),
        )

    async def list_facts(self, subject: str | None = None) -> list[dict]:
        if subject:
            return await self._all("SELECT * FROM facts WHERE subject = ? ORDER BY id", (subject,))
        return await self._all("SELECT * FROM facts ORDER BY id")

    # ---- reminders ----
    async def add_reminder(self, text: str, due_at: datetime,
                           urgency: str = "normal", created_by: str = "user") -> int:
        return await self._run(
            "INSERT INTO reminders (text, due_at, urgency, created_by) VALUES (?,?,?,?)",
            (text, to_utc_iso(due_at), urgency, created_by),
        )

    async def list_reminders(self, status: str | None = None) -> list[dict]:
        if status:
            return await self._all(
                "SELECT * FROM reminders WHERE status = ? ORDER BY due_at", (status,))
        return await self._all("SELECT * FROM reminders ORDER BY due_at")

    async def due_reminders(self) -> list[dict]:
        """Used by the Phase 4 scheduler: pending reminders whose time has come."""
        return await self._all(
            "SELECT * FROM reminders WHERE status = 'pending' AND due_at <= ? ORDER BY due_at",
            (to_utc_iso(datetime.now(timezone.utc)),),
        )

    async def set_reminder_status(self, reminder_id: int, status: str) -> bool:
        async with self._conn.execute(
            "UPDATE reminders SET status = ? WHERE id = ?", (status, reminder_id)
        ) as cur:
            await self._conn.commit()
            return cur.rowcount > 0

    # ---- messages ----
    async def add_message(self, session_id: str, role: str, content: str,
                          modality: str = "text", interrupted: bool = False,
                          interrupted_at_char: int | None = None) -> int:
        return await self._run(
            """INSERT INTO messages
               (session_id, role, content, modality, interrupted, interrupted_at_char)
               VALUES (?,?,?,?,?,?)""",
            (session_id, role, content, modality, int(interrupted), interrupted_at_char),
        )

    async def recent_messages(self, limit: int = 50,
                              session_id: str | None = None) -> list[dict]:
        if session_id:
            rows = await self._all(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit))
        else:
            rows = await self._all("SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        return rows[::-1]  # oldest first, ready for the chat screen

    # ---- affect ----
    async def log_affect(self, ts: str, sadness: float, anxiety: float,
                         valence: float, s_distress: float) -> None:
        await self._run(
            """INSERT INTO affect_log (ts, sadness, anxiety, valence, s_distress)
               VALUES (?,?,?,?,?)""",
            (ts, sadness, anxiety, valence, s_distress),
        )

    async def recent_affect(self, limit: int = 100) -> list[dict]:
        rows = await self._all("SELECT * FROM affect_log ORDER BY id DESC LIMIT ?", (limit,))
        return rows[::-1]