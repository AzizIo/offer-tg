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
        "brand_label": "Offer TG · сторонний оффер",
        "offer_sentence": "Пользователь {creator} предложил вам <b>{price} ⭐</b> за ваш подарок <a href=\"{link}\"><b>{gift}</b></a>.",
        "expiry_line": "Истекает через <b>{time}</b>.",
        "disclaimer": "<i>Неофициальный оффер. Stars не резервируются; оплата и передача подарка выполняются отдельно.</i>",
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
        "brand_label": "Offer TG · third-party offer",
        "offer_sentence": "The user {creator} offered you <b>{price} ⭐</b> for your gift <a href=\"{link}\"><b>{gift}</b></a>.",
        "expiry_line": "Expires in <b>{time}</b>.",
        "disclaimer": "<i>Unofficial offer. Stars are not reserved; payment and gift transfer happen separately.</i>",
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
    "zh": {
        "brand_label": "Offer TG · 第三方报价",
        "offer_sentence": "用户 {creator} 向您提出 <b>{price} ⭐</b> 的报价，购买您的礼物 <a href=\"{link}\"><b>{gift}</b></a>。",
        "expiry_line": "<b>{time}</b> 后过期。",
        "disclaimer": "<i>非 Telegram 官方报价。Stars 不会被预留；付款和礼物转移由双方另行完成。</i>",
        "accepted": "✅ <b>报价已接受</b>",
        "rejected": "❌ <b>报价已拒绝</b>",
        "cancelled": "↩️ <b>报价已取消</b>",
        "expired": "⌛ <b>报价已过期</b>",
        "accepted_body": "用户 <b>{actor}</b> 已接受以 <b>{price} ⭐</b> 购买礼物 <a href=\"{link}\"><b>{gift}</b></a> 的报价。",
        "rejected_body": "用户 <b>{actor}</b> 已拒绝礼物 <a href=\"{link}\"><b>{gift}</b></a> 的报价。",
        "cancelled_body": "发送者已取消礼物 <a href=\"{link}\"><b>{gift}</b></a> 的报价。",
        "expired_body": "礼物 <a href=\"{link}\"><b>{gift}</b></a> 的报价已失效。",
        "final_note": "礼物转移和付款由双方另行完成。机器人中的状态不代表礼物或 Stars 已转移。",
        "reject_button": "拒绝",
        "accept_button": "接受",
        "cancel_button": "取消报价",
        "how_button": "如何转移？",
        "open_gift": "查看礼物",
        "how_text": "❓ <b>如何转移收藏礼物</b>\n\n1. 打开 Telegram 个人资料 → 礼物。\n2. 选择收藏礼物。\n3. 如果可以，点击转移。\n4. 核对收件人并确认。\n\n⚠️ 转移前请自行核实交易和付款。",
        "creator_cannot": "发送者不能接受或拒绝自己的报价。",
        "wrong_recipient": "此报价是发给其他用户的。",
        "only_creator": "只有发送者可以取消此报价。",
        "not_found": "未找到报价。",
        "already_done": "此报价已处理。",
        "expired_alert": "此报价已过期。",
        "access_denied": "您无权执行此操作。",
    },
    "ar": {
        "brand_label": "Offer TG · عرض من خدمة خارجية",
        "offer_sentence": "عرض عليك المستخدم {creator} مبلغ <b>{price} ⭐</b> مقابل هديتك <a href=\"{link}\"><b>{gift}</b></a>.",
        "expiry_line": "ينتهي خلال <b>{time}</b>.",
        "disclaimer": "<i>عرض غير رسمي. لا يتم حجز النجوم؛ ويتفق الطرفان بشكل منفصل على الدفع ونقل الهدية.</i>",
        "accepted": "✅ <b>تم قبول العرض</b>",
        "rejected": "❌ <b>تم رفض العرض</b>",
        "cancelled": "↩️ <b>تم إلغاء العرض</b>",
        "expired": "⌛ <b>انتهت صلاحية العرض</b>",
        "accepted_body": "قبل المستخدم <b>{actor}</b> عرض شراء <a href=\"{link}\"><b>{gift}</b></a> مقابل <b>{price} ⭐</b>.",
        "rejected_body": "رفض المستخدم <b>{actor}</b> العرض الخاص بالهدية <a href=\"{link}\"><b>{gift}</b></a>.",
        "cancelled_body": "ألغى المنشئ العرض الخاص بالهدية <a href=\"{link}\"><b>{gift}</b></a>.",
        "expired_body": "لم يعد العرض الخاص بالهدية <a href=\"{link}\"><b>{gift}</b></a> متاحاً.",
        "final_note": "يتم تحويل الهدية والدفع بشكل منفصل بين الطرفين. حالة البوت لا تؤكد تحويل الهدية أو النجوم.",
        "reject_button": "رفض",
        "accept_button": "قبول",
        "cancel_button": "إلغاء العرض",
        "how_button": "كيفية التحويل؟",
        "open_gift": "فتح الهدية",
        "how_text": "❓ <b>كيفية تحويل هدية قابلة للجمع</b>\n\n1. افتح ملفك الشخصي في Telegram ثم الهدايا.\n2. اختر الهدية القابلة للجمع.\n3. اضغط على تحويل إذا كان متاحاً.\n4. تحقق من المستلم وأكد العملية.\n\n⚠️ تحقق بنفسك من الاتفاق والدفع قبل التحويل.",
        "creator_cannot": "لا يمكن لمنشئ العرض قبول عرضه أو رفضه.",
        "wrong_recipient": "هذا العرض موجّه إلى مستخدم آخر.",
        "only_creator": "يمكن لمنشئ العرض فقط إلغاؤه.",
        "not_found": "لم يتم العثور على العرض.",
        "already_done": "تمت معالجة هذا العرض بالفعل.",
        "expired_alert": "انتهت صلاحية هذا العرض.",
        "access_denied": "ليس لديك إذن لتنفيذ هذا الإجراء.",
    },
}


def tr(language: str, key: str) -> str:
    lang = language if language in MESSAGES else "ru"
    return MESSAGES[lang].get(key, MESSAGES["ru"].get(key, key))


def premium_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{escape(emoji_id, quote=True)}">{escape(fallback)}</tg-emoji>'


def remaining_time(expires_at: str | None, language: str = "ru") -> str:
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
    minutes = remainder // 60
    if language == "en":
        return f"{hours}h {minutes}m"
    if language == "zh":
        return f"{hours}小时{minutes}分钟"
    if language == "ar":
        return f"{hours} س {minutes} د"
    return f"{hours} ч. {minutes} мин."


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
    """Render a compact, clearly branded third-party offer.

    The Bot API cannot emit Telegram's centered system service message. Keep the
    offer content familiar, but visibly label it as Offer TG and disclose that
    this bot does not reserve Stars or transfer the gift.
    """
    language = str(offer.get("language") or "ru")
    creator_name = escape(str(offer["creator_name"]))
    try:
        creator_id = int(offer.get("creator_id") or 0)
    except (TypeError, ValueError):
        creator_id = 0
    creator = (
        f'<a href="tg://user?id={creator_id}">{creator_name}</a>'
        if creator_id > 0
        else creator_name
    )
    gift_name = escape(str(offer["gift_name"]))
    gift_link = escape(str(offer["gift_link"]), quote=True)
    price = format_stars(offer.get("price_stars") or offer.get("price") or 0)
    time_left = remaining_time(offer.get("expires_at"), language)

    return (
        f"<b>{tr(language, 'brand_label')}</b>\n"
        + tr(language, "offer_sentence").format(
            creator=creator,
            price=price,
            link=gift_link,
            gift=gift_name,
        )
        + "\n"
        + tr(language, "expiry_line").format(time=time_left)
        + "\n\n"
        + tr(language, "disclaimer")
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
