from offerbot.presentation import make_offer_text, make_resolved_text


def test_offer_text_escapes_user_content_and_discloses_manual_settlement():
    text = make_offer_text({
        "creator_name": "<script>alert(1)</script>",
        "gift_name": "<b>Gift</b>",
        "gift_link": "https://t.me/nft/Gift-1",
        "price_stars": 100,
        "expires_at": None,
        "language": "ru",
    })

    assert "<script>" not in text
    assert "&lt;script&gt;" in text
    assert "&lt;b&gt;Gift&lt;/b&gt;" in text
    assert "Stars не резервируются" in text


def test_accepted_text_does_not_claim_payment_or_transfer_completed():
    text = make_resolved_text(
        {
            "gift_name": "Gift #1",
            "gift_link": "https://t.me/nft/Gift-1",
            "price_stars": 100,
            "language": "ru",
        },
        "accepted",
        "Buyer",
    )

    assert "Предложение принято" in text
    assert "не подтверждает перевод подарка или Stars" in text



def test_stars_formatting_handles_large_numbers_and_legacy_decimals():
    from offerbot.presentation import format_stars

    assert format_stars("12000") == "12,000"
    assert format_stars("1.50") == "1.5"
    assert format_stars("12000.25") == "12,000.25"


def test_offer_card_uses_localized_chinese_and_arabic_labels():
    from offerbot.presentation import make_offer_text

    base = {
        "creator_id": 10,
        "creator_name": "Seller",
        "gift_name": "Gift",
        "gift_link": "https://t.me/nft/Gift-1",
        "price_stars": 100,
        "expires_at": None,
    }
    zh = make_offer_text({**base, "language": "zh"})
    ar = make_offer_text({**base, "language": "ar"})

    assert "Offer TG" in zh
    assert "Offer TG" in ar



def test_offer_card_matches_minimal_offer_wording_and_is_clearly_unofficial():
    text = make_offer_text({
        "creator_id": 42,
        "creator_name": "Seller",
        "gift_name": "Gift #123",
        "gift_link": "https://t.me/nft/Gift-123",
        "price_stars": 18000,
        "expires_at": None,
        "language": "en",
    })

    assert "Offer TG" in text
    assert "offered you <b>18,000 ⭐</b>" in text
    assert "your gift" in text
    assert "Unofficial offer" in text
    assert "Stars are not reserved" in text
    assert "From" not in text
    assert "Open gift" not in text
