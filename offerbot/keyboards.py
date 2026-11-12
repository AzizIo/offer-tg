from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .presentation import tr


REJECT_BUTTON_EMOJI_ID = "5985346521103604145"
ACCEPT_BUTTON_EMOJI_ID = "5985596818912712352"


def offer_keyboard(
    offer_id: int,
    language: str = "ru",
    *,
    custom_icons: bool = True,
) -> InlineKeyboardMarkup:
    """Render localized actions with Telegram custom-emoji button icons."""
    reject_kwargs = {"style": "danger"}
    accept_kwargs = {"style": "success"}
    if custom_icons:
        reject_kwargs["icon_custom_emoji_id"] = REJECT_BUTTON_EMOJI_ID
        accept_kwargs["icon_custom_emoji_id"] = ACCEPT_BUTTON_EMOJI_ID

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                tr(language, "reject_button"),
                callback_data=f"offer:reject:{offer_id}",
                **reject_kwargs,
            ),
            InlineKeyboardButton(
                tr(language, "accept_button"),
                callback_data=f"offer:accept:{offer_id}",
                **accept_kwargs,
            ),
        ],
    ])


def start_keyboard(owner_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 Подписки", callback_data="subscription:plans"),
            InlineKeyboardButton("👤 Поддержка", url=f"https://t.me/{owner_username.lstrip('@')}"),
        ],
        [InlineKeyboardButton("📖 Инструкция", callback_data="menu:help")],
    ])
