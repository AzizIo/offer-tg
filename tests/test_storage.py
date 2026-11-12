import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from offerbot.storage import (
    OfferAlreadyResolved,
    OfferExpired,
    OfferLimitReached,
    OfferPermissionDenied,
    Storage,
)


def make_storage(tmp_path):
    return Storage(tmp_path / "offers.sqlite3")


def create_offer(storage, recipient_id=None, daily_limit=20, ttl_hours=6):
    return storage.create_offer(
        creator_id=10,
        creator_name="Seller",
        creator_username="seller",
        gift_name="Gift #1",
        gift_link="https://t.me/nft/Gift-1",
        price_stars=120,
        ttl_hours=ttl_hours,
        recipient_id=recipient_id,
        daily_limit=daily_limit,
    )


def test_grant_access_expiry_and_revoke(tmp_path):
    storage = make_storage(tmp_path)
    storage.grant_access(10, "seller", "Seller", days=30, plan="vip", actor_id=99)

    access = storage.get_access(10)
    assert access is not None
    assert access["sub_type"] == "vip"
    assert storage.is_allowed(10) is True

    with storage.transaction(immediate=True) as db:
        db.execute(
            "UPDATE allowed_users SET expires_at = ? WHERE user_id = ?",
            ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), 10),
        )

    assert storage.is_allowed(10) is False
    assert storage.revoke_access(10, actor_id=99) is True
    assert storage.revoke_access(10, actor_id=99) is False


def test_targeted_offer_permissions_and_single_resolution(tmp_path):
    storage = make_storage(tmp_path)
    offer_id = create_offer(storage, recipient_id=22)

    with pytest.raises(OfferPermissionDenied):
        storage.resolve_offer(offer_id, actor_id=10, action="accepted")

    with pytest.raises(OfferPermissionDenied):
        storage.resolve_offer(offer_id, actor_id=33, action="accepted")

    result = storage.resolve_offer(offer_id, actor_id=22, action="accepted")
    assert result["status"] == "accepted"
    assert result["resolved_by"] == 22

    with pytest.raises(OfferAlreadyResolved):
        storage.resolve_offer(offer_id, actor_id=22, action="rejected")


def test_creator_can_cancel_but_other_user_cannot(tmp_path):
    storage = make_storage(tmp_path)
    offer_id = create_offer(storage)

    with pytest.raises(OfferPermissionDenied):
        storage.resolve_offer(offer_id, actor_id=22, action="cancelled")

    result = storage.resolve_offer(offer_id, actor_id=10, action="cancelled")
    assert result["status"] == "cancelled"


def test_open_offer_can_be_accepted_by_another_user(tmp_path):
    storage = make_storage(tmp_path)
    offer_id = create_offer(storage)

    with pytest.raises(OfferPermissionDenied):
        storage.resolve_offer(offer_id, actor_id=10, action="accepted")

    result = storage.resolve_offer(offer_id, actor_id=22, action="accepted")
    assert result["status"] == "accepted"


def test_expired_offer_status_is_committed_before_error(tmp_path):
    storage = make_storage(tmp_path)
    offer_id = create_offer(storage)

    with storage.transaction(immediate=True) as db:
        db.execute(
            "UPDATE offers SET expires_at = ? WHERE id = ?",
            ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), offer_id),
        )

    with pytest.raises(OfferExpired):
        storage.resolve_offer(offer_id, actor_id=22, action="accepted")

    assert storage.get_offer(offer_id)["status"] == "expired"


def test_daily_offer_limit_is_enforced_atomically(tmp_path):
    storage = make_storage(tmp_path)
    create_offer(storage, daily_limit=1)

    with pytest.raises(OfferLimitReached):
        create_offer(storage, daily_limit=1)


def test_migrates_original_database_without_dropping_users_or_offers(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE allowed_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            granted_at TEXT
        );
        CREATE TABLE offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER NOT NULL,
            creator_name TEXT NOT NULL,
            gift_name TEXT NOT NULL,
            gift_link TEXT NOT NULL,
            price TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            accepted_at TEXT
        );
    """)
    created = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    connection.execute(
        "INSERT INTO allowed_users VALUES (?, ?, ?, ?)",
        (10, "seller", "Seller", created),
    )
    connection.execute(
        "INSERT INTO offers(creator_id, creator_name, gift_name, gift_link, price, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (10, "Seller", "Gift #1", "https://t.me/nft/Gift-1", "120", created),
    )
    connection.commit()
    connection.close()

    storage = Storage(path)

    assert storage.is_allowed(10) is True
    migrated = storage.get_offer(1)
    assert migrated is not None
    assert migrated["status"] == "pending"
    expiry = datetime.fromisoformat(migrated["expires_at"])
    assert expiry > datetime.now(timezone.utc)
    assert migrated["recipient_id"] is None
