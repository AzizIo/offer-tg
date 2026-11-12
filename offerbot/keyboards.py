from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .presentation import EMOJI, tr


def offer_keyboard(offer_id: int, language: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                tr(language, "reject_button"),
                callback_data=f"offer:reject:{offer_id}",
                icon_custom_emoji_id=EMOJI["reject"],
            ),
            InlineKeyboardButton(
                tr(language, "accept_button"),
                callback_data=f"offer:accept:{offer_id}",
                icon_custom_emoji_id=EMOJI["accept"],
            ),
        ],
    ])


def resolved_keyboard(offer: dict, language: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                tr(language, "open_gift"),
                url=offer["gift_link"],
            ),
            InlineKeyboardButton(
                tr(language, "how_button"),
                callback_data=f"offer:how:{int(offer['id'])}",
            ),
        ]
    ])


def start_keyboard(owner_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 Подписки", callback_data="subscription:plans"),
            InlineKeyboardButton("👤 Поддержка", url=f"https://t.me/{owner_username.lstrip('@')}"),
        ],
        [InlineKeyboardButton("📖 Инструкция", callback_data="menu:help")],
    ])
