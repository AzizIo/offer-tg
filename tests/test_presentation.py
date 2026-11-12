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
    assert "не резервирует Stars" in text


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
