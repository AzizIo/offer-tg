from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


VALID_PLANS = {"normal", "vip"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


class OfferError(Exception):
    pass


class OfferNotFound(OfferError):
    pass


class OfferAlreadyResolved(OfferError):
    pass


class OfferExpired(OfferError):
    pass


class OfferPermissionDenied(OfferError):
    pass


class OfferLimitReached(OfferError):
    pass


class Storage:
    """SQLite persistence with additive migration from the original bot schema."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        if str(self.path) != ":memory:":
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    @contextmanager
    def transaction(self, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def read_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
        return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}

    def initialize(self) -> None:
        with self.transaction(immediate=True) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    granted_at TEXT,
                    expires_at TEXT,
                    sub_type TEXT DEFAULT 'normal'
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creator_id INTEGER NOT NULL,
                    creator_name TEXT NOT NULL,
                    creator_username TEXT,
                    gift_name TEXT NOT NULL,
                    gift_link TEXT NOT NULL,
                    price TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    expires_at TEXT,
                    accepted_at TEXT
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER,
                    details TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)

            migrations = {
                "allowed_users": {
                    "expires_at": "TEXT",
                    "sub_type": "TEXT DEFAULT 'normal'",
                },
                "offers": {
                    "creator_username": "TEXT",
                    "expires_at": "TEXT",
                    "accepted_at": "TEXT",
                    "recipient_id": "INTEGER",
                    "resolved_by": "INTEGER",
                    "resolved_at": "TEXT",
                    "updated_at": "TEXT",
                    "language": "TEXT NOT NULL DEFAULT 'ru'",
                    "source_chat_id": "INTEGER",
                    "source_message_id": "INTEGER",
                },
            }
            for table, columns in migrations.items():
                existing = self._columns(db, table)
                for name, definition in columns.items():
                    if name not in existing:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

            db.execute("""
                UPDATE allowed_users
                SET sub_type = 'normal'
                WHERE sub_type IS NULL OR sub_type NOT IN ('normal', 'vip')
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_offers_creator_created ON offers(creator_id, created_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_offers_status_expiry ON offers(status, expires_at)")

        # Migrate old pending offers to an expiry timestamp without changing their
        # original created_at value or relying on SQLite's locale-dependent strings.
        with self.transaction(immediate=True) as db:
            rows = db.execute(
                "SELECT id, created_at FROM offers WHERE status = 'pending' AND expires_at IS NULL"
            ).fetchall()
            for row in rows:
                try:
                    created = datetime.fromisoformat(row["created_at"])
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    expires = (created + timedelta(hours=6)).astimezone(timezone.utc).isoformat()
                except (TypeError, ValueError):
                    expires = utc_now().isoformat()
                db.execute("UPDATE offers SET expires_at = ? WHERE id = ?", (expires, row["id"]))

    def grant_access(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        days: int = 0,
        plan: str = "normal",
        actor_id: int | None = None,
    ) -> None:
        if user_id <= 0 or days < 0 or plan not in VALID_PLANS:
            raise ValueError("Invalid user ID, duration, or subscription plan")
        now = utc_now()
        expires = (now + timedelta(days=days)).isoformat() if days else None
        with self.transaction(immediate=True) as db:
            db.execute("""
                INSERT INTO allowed_users(user_id, username, first_name, granted_at, expires_at, sub_type)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(excluded.username, allowed_users.username),
                    first_name = COALESCE(excluded.first_name, allowed_users.first_name),
                    granted_at = excluded.granted_at,
                    expires_at = excluded.expires_at,
                    sub_type = excluded.sub_type
            """, (user_id, username, first_name, now.isoformat(), expires, plan))
            if actor_id is not None:
                db.execute("""
                    INSERT INTO audit_log(actor_id, action, entity_type, entity_id, details, created_at)
                    VALUES (?, 'subscription.grant', 'user', ?, ?, ?)
                """, (actor_id, user_id, f"plan={plan};days={days}", now.isoformat()))

    def revoke_access(self, user_id: int, actor_id: int) -> bool:
        with self.transaction(immediate=True) as db:
            cursor = db.execute("DELETE FROM allowed_users WHERE user_id = ?", (user_id,))
            changed = cursor.rowcount > 0
            if changed:
                db.execute("""
                    INSERT INTO audit_log(actor_id, action, entity_type, entity_id, details, created_at)
                    VALUES (?, 'subscription.revoke', 'user', ?, '', ?)
                """, (actor_id, user_id, iso_now()))
            return changed

    def get_access(self, user_id: int) -> dict | None:
        with self.read_connection() as db:
            row = db.execute(
                "SELECT user_id, username, first_name, expires_at, sub_type FROM allowed_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        expires = row["expires_at"]
        if expires:
            try:
                parsed = datetime.fromisoformat(expires)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed <= utc_now():
                    return None
            except ValueError:
                return None
        return dict(row)

    def is_allowed(self, user_id: int) -> bool:
        return self.get_access(user_id) is not None

    def create_offer(
        self,
        creator_id: int,
        creator_name: str,
        creator_username: str,
        gift_name: str,
        gift_link: str,
        price_stars: int,
        ttl_hours: int,
        language: str = "ru",
        recipient_id: int | None = None,
        daily_limit: int = 20,
    ) -> int:
        if creator_id <= 0 or price_stars <= 0 or ttl_hours <= 0 or daily_limit <= 0:
            raise ValueError("Invalid offer parameters")
        if recipient_id is not None and (recipient_id <= 0 or recipient_id == creator_id):
            raise ValueError("Recipient must be a different Telegram user")
        now = utc_now()
        expires = now + timedelta(hours=ttl_hours)
        with self.transaction(immediate=True) as db:
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            count = db.execute(
                "SELECT COUNT(*) AS amount FROM offers WHERE creator_id = ? AND created_at >= ?",
                (creator_id, day_start),
            ).fetchone()["amount"]
            if count >= daily_limit:
                raise OfferLimitReached("Daily offer limit reached")
            cursor = db.execute("""
                INSERT INTO offers(
                    creator_id, creator_name, creator_username, gift_name, gift_link,
                    price, status, created_at, expires_at, recipient_id, language
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """, (
                creator_id, creator_name[:128], creator_username or "", gift_name,
                gift_link, str(price_stars), now.isoformat(), expires.isoformat(),
                recipient_id, language,
            ))
            offer_id = int(cursor.lastrowid)
            db.execute("""
                INSERT INTO audit_log(actor_id, action, entity_type, entity_id, details, created_at)
                VALUES (?, 'offer.created', 'offer', ?, ?, ?)
            """, (creator_id, offer_id, f"price_stars={price_stars};recipient_id={recipient_id or ''}", now.isoformat()))
            return offer_id

    def set_offer_message(self, offer_id: int, chat_id: int, message_id: int) -> None:
        with self.transaction(immediate=True) as db:
            db.execute(
                "UPDATE offers SET source_chat_id = ?, source_message_id = ? WHERE id = ?",
                (chat_id, message_id, offer_id),
            )

    def get_offer(self, offer_id: int) -> dict | None:
        with self.read_connection() as db:
            row = db.execute("""
                SELECT id, creator_id, creator_name, creator_username, gift_name, gift_link,
                       price, status, expires_at, recipient_id, resolved_by, resolved_at,
                       language, source_chat_id, source_message_id
                FROM offers WHERE id = ?
            """, (offer_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        # Preserve historical decimal prices from the legacy parser; new offers use integer Stars.
        result["price_stars"] = result["price"]
        return result

    def resolve_offer(self, offer_id: int, actor_id: int, action: str) -> dict:
        if action not in {"accepted", "rejected", "cancelled"}:
            raise ValueError("Unsupported offer action")
        now = utc_now()
        now_iso = now.isoformat()
        expired = False
        resolved_offer: dict | None = None

        with self.transaction(immediate=True) as db:
            row = db.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
            if not row:
                raise OfferNotFound("Offer not found")
            offer = dict(row)
            if offer["status"] != "pending":
                raise OfferAlreadyResolved(f"Offer already has status {offer['status']}")

            expiry_value = offer.get("expires_at")
            try:
                expiry = datetime.fromisoformat(expiry_value) if expiry_value else now
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                expiry = now

            if expiry <= now:
                db.execute("""
                    UPDATE offers SET status = 'expired', updated_at = ?, resolved_at = ?
                    WHERE id = ? AND status = 'pending'
                """, (now_iso, now_iso, offer_id))
                db.execute("""
                    INSERT INTO audit_log(actor_id, action, entity_type, entity_id, details, created_at)
                    VALUES (?, 'offer.expired', 'offer', ?, '', ?)
                """, (actor_id, offer_id, now_iso))
                expired = True
            else:
                creator_id = int(offer["creator_id"])
                recipient_id = offer.get("recipient_id")
                if action == "cancelled":
                    if actor_id != creator_id:
                        raise OfferPermissionDenied("Only the offer creator may cancel it")
                else:
                    if actor_id == creator_id:
                        raise OfferPermissionDenied("The offer creator cannot accept or reject their own offer")
                    if recipient_id is not None and actor_id != int(recipient_id):
                        raise OfferPermissionDenied("This offer is addressed to another Telegram user")

                updated = db.execute("""
                    UPDATE offers
                    SET status = ?, accepted_at = ?, resolved_by = ?, resolved_at = ?, updated_at = ?
                    WHERE id = ? AND status = 'pending'
                """, (
                    action,
                    now_iso if action == "accepted" else None,
                    actor_id, now_iso, now_iso, offer_id,
                ))
                if updated.rowcount != 1:
                    raise OfferAlreadyResolved("Offer was resolved by another action")
                db.execute("""
                    INSERT INTO audit_log(actor_id, action, entity_type, entity_id, details, created_at)
                    VALUES (?, ?, 'offer', ?, '', ?)
                """, (actor_id, f"offer.{action}", offer_id, now_iso))
                offer["status"] = action
                offer["resolved_by"] = actor_id
                offer["resolved_at"] = now_iso
                # Keep legacy decimal price strings readable in the card renderer.
                offer["price_stars"] = offer["price"]
                resolved_offer = offer

        if expired:
            raise OfferExpired("Offer has expired")
        if resolved_offer is None:
            raise OfferAlreadyResolved("Offer could not be resolved")
        return resolved_offer

    def expire_due_offers(self, limit: int = 500) -> list[int]:
        now = iso_now()
        with self.transaction(immediate=True) as db:
            rows = db.execute("""
                SELECT id FROM offers
                WHERE status = 'pending' AND expires_at IS NOT NULL AND expires_at <= ?
                ORDER BY expires_at LIMIT ?
            """, (now, limit)).fetchall()
            ids = [int(row["id"]) for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                db.execute(
                    f"UPDATE offers SET status = 'expired', updated_at = ?, resolved_at = ? WHERE id IN ({placeholders}) AND status = 'pending'",
                    [now, now, *ids],
                )
                db.executemany("""
                    INSERT INTO audit_log(actor_id, action, entity_type, entity_id, details, created_at)
                    VALUES (0, 'offer.expired', 'offer', ?, '', ?)
                """, [(offer_id, now) for offer_id in ids])
            return ids

    def list_user_offers(self, user_id: int, limit: int = 10) -> list[dict]:
        with self.read_connection() as db:
            rows = db.execute("""
                SELECT id, creator_id, creator_name, gift_name, gift_link, price,
                       status, created_at, expires_at, recipient_id, resolved_by
                FROM offers
                WHERE creator_id = ? OR recipient_id = ? OR resolved_by = ?
                ORDER BY id DESC LIMIT ?
            """, (user_id, user_id, user_id, limit)).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict[str, int]:
        with self.read_connection() as db:
            users = db.execute("SELECT COUNT(*) AS amount FROM allowed_users").fetchone()["amount"]
            offers = db.execute("SELECT COUNT(*) AS amount FROM offers").fetchone()["amount"]
            pending = db.execute("SELECT COUNT(*) AS amount FROM offers WHERE status = 'pending'").fetchone()["amount"]
            accepted = db.execute("SELECT COUNT(*) AS amount FROM offers WHERE status = 'accepted'").fetchone()["amount"]
            expired = db.execute("SELECT COUNT(*) AS amount FROM offers WHERE status = 'expired'").fetchone()["amount"]
        return {
            "users": int(users),
            "offers": int(offers),
            "pending": int(pending),
            "accepted": int(accepted),
            "expired": int(expired),
        }
