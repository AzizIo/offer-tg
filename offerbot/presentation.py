from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any


EMOJI = {
    "gift": "6037175527846975726",
    "star": "5897792062291449826",
    "accept": "5985596818912712352",
    "reject": "5985346521103604145",
    "cancel": "5217881018299595934",
}


MESSAGES = {
    "ru": {
        "offer_title": "Предложение о покупке подарка",
        "price_for": "за",
        "seller": "Отправитель",
        "expires": "Действительно ещё",
        "external_note": "Это предложение стороннего сервиса. Бот не резервирует Stars и не выполняет передачу подарка.",
        "accepted": "✅ <b>Предложение принято</b>",
        "rejected": "❌ <b>Предложение отклонено</b>",
        "cancelled": "↩️ <b>Предложение отменено</b>",
        "expired": "⌛ <b>Срок предложения истёк</b>",
        "accepted_body": "Пользователь <b>{actor}</b> принял предложение за <b>{price} ⭐</b> по подарку <a href=\"{link}\"><b>{gift}</b></a>.",
        "rejected_body": "Пользователь <b>{actor}</b> отклонил предложение по подарку <a href=\"{link}\"><b>{gift}</b></a>.",
        "cancelled_body": "Автор отменил предложение по подарку <a href=\"{link}\"><b>{gift}</b></a>.",
        "expired_body": "Предложение по подарку <a href=\"{link}\"><b>{gift}</b></a> больше не активно.",
        "final_note": "Передача подарка и расчёт выполняются сторонами отдельно. Статус в боте не подтверждает перевод подарка или Stars.",
        "reject_button": "Отклонить",
        "accept_button": "Принять",
        "cancel_button": "Отменить оффер",
        "how_button": "Как передать?",
        "open_gift": "Открыть подарок",
        "how_text": "❓ <b>Как передать коллекционный подарок</b>\n\n1. Откройте профиль Telegram → «Подарки».\n2. Выберите нужный коллекционный подарок.\n3. Нажмите «Передать» / Transfer, если эта возможность доступна.\n4. Проверьте получателя и подтвердите передачу.\n\n⚠️ Передавайте подарок только после самостоятельной проверки договорённостей и оплаты.",
        "creator_cannot": "Автор не может принять или отклонить собственный оффер.",
        "wrong_recipient": "Этот оффер адресован другому пользователю.",
        "only_creator": "Отменить оффер может только его автор.",
        "not_found": "Оффер не найден.",
        "already_done": "Оффер уже обработан.",
        "expired_alert": "Срок действия оффера истёк.",
        "access_denied": "У вас нет доступа к этому действию.",
    },
    "en": {
        "offer_title": "Gift purchase offer",
        "price_for": "for",
        "seller": "From",
        "expires": "Expires in",
        "external_note": "This offer is provided by a third-party service. The bot does not reserve Stars or transfer gifts.",
        "accepted": "✅ <b>Offer accepted</b>",
        "rejected": "❌ <b>Offer declined</b>",
        "cancelled": "↩️ <b>Offer cancelled</b>",
        "expired": "⌛ <b>Offer expired</b>",
        "accepted_body": "<b>{actor}</b> accepted the offer of <b>{price} ⭐</b> for <a href=\"{link}\"><b>{gift}</b></a>.",
        "rejected_body": "<b>{actor}</b> declined the offer for <a href=\"{link}\"><b>{gift}</b></a>.",
        "cancelled_body": "The creator cancelled the offer for <a href=\"{link}\"><b>{gift}</b></a>.",
        "expired_body": "The offer for <a href=\"{link}\"><b>{gift}</b></a> is no longer active.",
        "final_note": "Gift transfer and payment are handled separately by the parties. This bot status does not confirm either transfer.",
        "reject_button": "Decline",
        "accept_button": "Accept",
        "cancel_button": "Cancel offer",
        "how_button": "How to transfer?",
        "open_gift": "Open gift",
        "how_text": "❓ <b>How to transfer a collectible gift</b>\n\n1. Open your Telegram profile → Gifts.\n2. Select the collectible gift.\n3. Choose Transfer if available.\n4. Verify the recipient and confirm.\n\n⚠️ Independently verify the deal and payment before transferring.",
        "creator_cannot": "The creator cannot accept or decline their own offer.",
        "wrong_recipient": "This offer is addressed to another user.",
        "only_creator": "Only the creator can cancel this offer.",
        "not_found": "Offer not found.",
        "already_done": "This offer has already been processed.",
        "expired_alert": "This offer has expired.",
        "access_denied": "You are not allowed to perform this action.",
    },
}


def tr(language: str, key: str) -> str:
    lang = language if language in MESSAGES else "ru"
    return MESSAGES[lang].get(key, MESSAGES["ru"].get(key, key))


def premium_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{escape(emoji_id, quote=True)}">{escape(fallback)}</tg-emoji>'


def remaining_time(expires_at: str | None) -> str:
    if not expires_at:
        return "—"
    try:
        expires = datetime.fromisoformat(expires_at)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        seconds = max(0, int((expires - datetime.now(timezone.utc)).total_seconds()))
    except (TypeError, ValueError):
        return "—"
    hours, remainder = divmod(seconds, 3600)
    return f"{hours} ч. {remainder // 60} мин."


def format_stars(value: Any) -> str:
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise InvalidOperation
        normalized = format(amount.normalize(), "f")
        whole, separator, fraction = normalized.partition(".")
        whole_text = f"{int(whole):,}"
        return whole_text + (f".{fraction}" if separator else "")
    except (InvalidOperation, ValueError, TypeError):
        return escape(str(value))


def make_offer_text(offer: dict[str, Any]) -> str:
    language = str(offer.get("language") or "ru")
    creator = escape(str(offer["creator_name"]))
    gift_name = escape(str(offer["gift_name"]))
    gift_link = escape(str(offer["gift_link"]), quote=True)
    price = format_stars(offer.get("price_stars") or offer.get("price") or 0)
    gift = premium_emoji(EMOJI["gift"], "🎁")
    star = premium_emoji(EMOJI["star"], "⭐")
    return (
        f"{gift} <b>{tr(language, 'offer_title')}</b>\n\n"
        f"<b>{price} {star}</b> {tr(language, 'price_for')} "
        f'<a href="{gift_link}"><b>{gift_name}</b></a>\n'
        f"{tr(language, 'seller')}: <b>{creator}</b>\n"
        f"{tr(language, 'expires')}: <b>{remaining_time(offer.get('expires_at'))}</b>\n\n"
        f"<i>{tr(language, 'external_note')}</i>"
    )


def make_resolved_text(offer: dict[str, Any], status: str, actor_name: str) -> str:
    language = str(offer.get("language") or "ru")
    actor = escape(actor_name)
    gift = escape(str(offer["gift_name"]))
    link = escape(str(offer["gift_link"]), quote=True)
    price = format_stars(offer.get("price_stars") or offer.get("price") or 0)
    title_key = status if status in {"accepted", "rejected", "cancelled", "expired"} else "expired"
    body_key = f"{title_key}_body"
    body = tr(language, body_key).format(actor=actor, gift=gift, link=link, price=price)
    return f"{tr(language, title_key)}\n\n{body}\n\n<i>{tr(language, 'final_note')}</i>"
