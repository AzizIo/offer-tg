from offerbot.keyboards import (
    ACCEPT_BUTTON_EMOJI_ID,
    REJECT_BUTTON_EMOJI_ID,
    offer_keyboard,
)


def test_offer_keyboard_uses_the_requested_custom_emoji_ids():
    markup = offer_keyboard(offer_id=123, language="ru")
    reject, accept = markup.inline_keyboard[0]

    assert reject.text == "Отклонить"
    assert reject.callback_data == "offer:reject:123"
    assert reject.icon_custom_emoji_id == REJECT_BUTTON_EMOJI_ID
    assert reject.icon_custom_emoji_id == "5985346521103604145"
    assert reject.style is None

    assert accept.text == "Принять"
    assert accept.callback_data == "offer:accept:123"
    assert accept.icon_custom_emoji_id == ACCEPT_BUTTON_EMOJI_ID
    assert accept.icon_custom_emoji_id == "5985596818912712352"
    assert accept.style is None


def test_offer_keyboard_can_fall_back_without_custom_emoji():
    markup = offer_keyboard(offer_id=456, language="en", custom_icons=False)
    decline, accept = markup.inline_keyboard[0]

    assert decline.text == "Decline"
    assert decline.icon_custom_emoji_id is None
    assert accept.text == "Accept"
    assert accept.icon_custom_emoji_id is None
