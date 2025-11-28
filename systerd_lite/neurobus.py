"""SQLite-backed NeuroBus implementation with WAL mode and auto-cleanup."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Literal, Optional

logger = logging.getLogger(__name__)

EventKind = Literal["event", "command", "learning"]


class NeuroBus:
    def __init__(self, storage: Path, max_rows: int = 100_000, retention_days: int = 30) -> None:
        self.storage = storage
        self.max_rows = max_rows
        self.retention_days = retention_days
        self.storage.parent.mkdir(parents=True, exist_ok=True)
        
        # Open with error handling
        try:
            self._conn = sqlite3.connect(
                self.storage,
                check_same_thread=False,  # Allow multi-threaded access
                timeout=10.0,  # 10s timeout for lock acquisition
            )
            
            # Enable WAL mode for better concurrency
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and speed
            self._conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            self._conn.execute("PRAGMA temp_store=MEMORY")
            
            # Create schema
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    ts REAL NOT NULL
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_topic ON messages(topic)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_kind ON messages(kind)")
            self._conn.commit()
            
            # Check database integrity
            self._check_integrity()
            
            logger.info(f"NeuroBus initialized: {self.storage} (max_rows={max_rows}, retention={retention_days}d)")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize NeuroBus database: {e}")
            raise
    
    def _check_integrity(self) -> None:
        """Check database integrity and repair if needed."""
        try:
            result = self._conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                logger.warning(f"NeuroBus database integrity check failed: {result[0]}")
                logger.info("Attempting to recover database...")
                self._conn.execute("REINDEX")
                self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database integrity check failed: {e}")

    def close(self) -> None:
        self._conn.close()

    def publish(self, kind: EventKind, topic: str, payload: Dict[str, Any]) -> None:
        try:
            self._conn.execute(
                "INSERT INTO messages(kind, topic, payload, ts) VALUES (?, ?, ?, ?)",
                (kind, topic, json.dumps(payload), time.time()),
            )
            self._conn.commit()
            self._enforce_retention()
        except sqlite3.Error as e:
            logger.error(f"Failed to publish to NeuroBus: {e}")
            # Try to recover connection
            try:
                self._conn.rollback()
            except:
                pass

    def record_event(self, topic: str, payload: Dict[str, Any]) -> None:
        self.publish("event", topic, payload)

    def record_command(self, topic: str, payload: Dict[str, Any]) -> None:
        self.publish("command", topic, payload)

    def record_learning(self, topic: str, payload: Dict[str, Any]) -> None:
        self.publish("learning", topic, payload)

    def query(
        self,
        *,
        topic: Optional[str] = None,
        kind: Optional[EventKind] = None,
        limit: int = 100,
    ) -> Iterable[Dict[str, Any]]:
        sql = "SELECT kind, topic, payload, ts FROM messages"
        clauses = []
        params: list[Any] = []
        if topic:
            clauses.append("topic = ?")
            params.append(topic)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        cur = self._conn.execute(sql, params)
        for row in cur.fetchall():
            yield {
                "kind": row[0],
                "topic": row[1],
                "payload": json.loads(row[2]),
                "ts": row[3],
            }

    def _enforce_retention(self) -> None:
        """Enforce both row count and time-based retention."""
        try:
            # Time-based retention (delete old events)
            if self.retention_days > 0:
                cutoff = time.time() - (self.retention_days * 86400)
                result = self._conn.execute(
                    "DELETE FROM messages WHERE ts < ?",
                    (cutoff,)
                )
                deleted_time = result.rowcount
                if deleted_time > 0:
                    logger.debug(f"Deleted {deleted_time} old messages (older than {self.retention_days} days)")
            
            # Row count limit
            cur = self._conn.execute("SELECT COUNT(*) FROM messages")
            count = cur.fetchone()[0]
            if count > self.max_rows:
                to_delete = count - self.max_rows
                self._conn.execute(
                    "DELETE FROM messages WHERE id IN (SELECT id FROM messages ORDER BY id ASC LIMIT ?)",
                    (to_delete,),
                )
                logger.debug(f"Deleted {to_delete} excess messages (row limit: {self.max_rows})")
            
            self._conn.commit()
            
            # Periodic vacuum (every 1000th call)
            if count % 1000 == 0:
                logger.debug("Running VACUUM on NeuroBus database")
                self._conn.execute("VACUUM")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to enforce retention: {e}")

    def count(self) -> int:
        """Return total number of messages stored in NeuroBus."""
        try:
            cur = self._conn.execute("SELECT COUNT(1) FROM messages")
            val = cur.fetchone()
            return int(val[0]) if val and val[0] is not None else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to count NeuroBus messages: {e}")
            return 0

    def count_by_kind(self, kind: EventKind) -> int:
        """Return number of messages for a particular kind (event/command/learning)."""
        try:
            cur = self._conn.execute("SELECT COUNT(1) FROM messages WHERE kind = ?", (kind,))
            val = cur.fetchone()
            return int(val[0]) if val and val[0] is not None else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to count NeuroBus messages by kind={kind}: {e}")
            return 0

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
