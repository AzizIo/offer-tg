from offerbot.parser import parse_offer_text


def test_parse_legacy_russian_format_and_infer_gift_name():
    parsed = parse_offer_text("!продаёшь? https://t.me/nft/Gift-123 100 ru")

    assert parsed is not None
    assert parsed.gift_name == "Gift #123"
    assert parsed.gift_link == "https://t.me/nft/Gift-123"
    assert parsed.price_stars == 100
    assert parsed.language == "ru"


def test_price_is_read_after_link_not_guessed_from_largest_number():
    parsed = parse_offer_text("Royal 2024 https://t.me/nft/Gift-987 45 ru")

    assert parsed is not None
    assert parsed.gift_name == "Royal 2024"
    assert parsed.price_stars == 45


def test_custom_gift_name_and_english_command():
    parsed = parse_offer_text("!offer Rare Gift https://t.me/nft/MyGift-42 250 en")

    assert parsed is not None
    assert parsed.gift_name == "Rare Gift"
    assert parsed.price_stars == 250
    assert parsed.language == "en"


def test_rejects_decimal_zero_and_non_telegram_links():
    assert parse_offer_text("https://t.me/nft/Gift-1 1.5 ru") is None
    assert parse_offer_text("https://t.me/nft/Gift-1 0 ru") is None
    assert parse_offer_text("https://example.com/nft/Gift-1 100 ru") is None


def test_rejects_missing_price():
    assert parse_offer_text("https://t.me/nft/Gift-1") is None
