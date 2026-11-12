from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .presentation import tr


def offer_keyboard(offer_id: int, language: str = "ru") -> InlineKeyboardMarkup:
    """Two primary actions, matching the minimal offer action layout."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                tr(language, "reject_button"),
                callback_data=f"offer:reject:{offer_id}",
            ),
            InlineKeyboardButton(
                tr(language, "accept_button"),
                callback_data=f"offer:accept:{offer_id}",
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
