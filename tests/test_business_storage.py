from datetime import timedelta

from offerbot.storage import Storage, iso_now, utc_now


def test_business_contacts_require_enabled_connection_and_reply_permission(tmp_path):
    storage = Storage(tmp_path / "business.db")
    storage.upsert_business_connection("conn-1", owner_id=100, is_enabled=True, can_reply=False)
    storage.record_business_contact(
        "conn-1", chat_id=200, user_id=200, username="customer", display_name="Customer"
    )
    assert storage.list_business_contacts(owner_id=100) == []

    storage.upsert_business_connection("conn-1", owner_id=100, is_enabled=True, can_reply=True)
    storage.record_business_contact(
        "conn-1", chat_id=200, user_id=200, username="customer", display_name="Customer"
    )
    contacts = storage.list_business_contacts(owner_id=100)
    assert len(contacts) == 1
    assert contacts[0]["chat_id"] == 200
    assert contacts[0]["connection_id"] == "conn-1"


def test_business_contact_lookup_is_scoped_to_owner_and_recent_activity(tmp_path):
    storage = Storage(tmp_path / "business.db")
    storage.upsert_business_connection("conn-1", owner_id=100, is_enabled=True, can_reply=True)
    storage.record_business_contact(
        "conn-1", chat_id=200, user_id=200, username=None, display_name="Customer"
    )
    contact = storage.list_business_contacts(owner_id=100)[0]

    assert storage.get_business_contact(contact["id"], owner_id=100) is not None
    assert storage.get_business_contact(contact["id"], owner_id=999) is None

    old_timestamp = (utc_now() - timedelta(hours=25)).isoformat()
    with storage.transaction(immediate=True) as db:
        db.execute(
            "UPDATE business_contacts SET last_seen_at = ? WHERE id = ?",
            (old_timestamp, contact["id"]),
        )
    assert storage.list_business_contacts(owner_id=100) == []
    assert storage.get_business_contact(contact["id"], owner_id=100) is None
