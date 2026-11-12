#!/usr/bin/env python3
"""
Telegram NFT Gift Offer Bot — Final version with Premium emoji, Normal/VIP, protection
"""

import logging
import os
import re
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    LinkPreviewOptions,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import TelegramError

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8967318153:AAHuOE1gCao9HVWzvlvnprINEYyw0mvNrMc"
DB_PATH = "offers.db"
OWNER_SECRET = "meowner11"
OFFER_TTL_HOURS = 6
SUB_CHANNEL = "easynftch"
OWNER_USERNAME = "RuslanArasov"

WELCOME_PHOTO = "welcome.jpg"
OWNER_PHOTO = "owner.jpg"

# Premium emoji IDs
EMOJI = {
    "accept": "5985596818912712352",
    "reject": "5985346521103604145",
    "star": "5897792062291449826",
    "gear": "5341715473882955310",
    "check": "5350486389806868244",
    "crown": "6271387924223234127",
    "instruction": "5404515205784806076",
    "step2": "5954045241831987858",
    "important": "5287767094052543762",
    "step4": "5253687331717659694",
    "explanation": "5404515205784806076",
    "exclamation": "5217881018299595934",
    "transfer": "5264710902153767489",
}

def pe(emoji_id: str, fallback: str = "•") -> str:
    """Premium emoji HTML"""
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

# ================== ЛОГИРОВАНИЕ ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


# ================== БАЗА ДАННЫХ ==================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS allowed_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            granted_at TEXT,
            expires_at TEXT,
            sub_type TEXT DEFAULT 'normal'
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER NOT NULL,
            creator_name TEXT NOT NULL,
            creator_username TEXT,
            gift_name TEXT NOT NULL,
            gift_link TEXT NOT NULL,
            price TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            expires_at TEXT,
            accepted_at TEXT
        )
        """
    )
    for sql in [
        "ALTER TABLE allowed_users ADD COLUMN expires_at TEXT",
        "ALTER TABLE allowed_users ADD COLUMN sub_type TEXT DEFAULT 'normal'",
        "ALTER TABLE offers ADD COLUMN creator_username TEXT",
        "ALTER TABLE offers ADD COLUMN expires_at TEXT",
    ]:
        try:
            c.execute(sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


def is_allowed(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT expires_at FROM allowed_users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    expires = row[0]
    if not expires:
        return True
    try:
        return datetime.fromisoformat(expires) > datetime.now(timezone.utc)
    except Exception:
        return True


def get_sub_type(user_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT sub_type FROM allowed_users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else "normal"


def grant_access(user_id: int, username: Optional[str], first_name: Optional[str], days: int = 0, sub_type: str = "normal"):
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=days)).isoformat() if days > 0 else None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO allowed_users (user_id, username, first_name, granted_at, expires_at, sub_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, username or "", first_name or "", now.isoformat(), expires, sub_type),
    )
    conn.commit()
    conn.close()


def create_offer(creator_id, creator_name, creator_username, gift_name, gift_link, price, ttl_hours=OFFER_TTL_HOURS) -> int:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=ttl_hours)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO offers (creator_id, creator_name, creator_username, gift_name, gift_link, price, status, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (creator_id, creator_name, creator_username or "", gift_name, gift_link, price, now.isoformat(), expires.isoformat()),
    )
    offer_id = c.lastrowid
    conn.commit()
    conn.close()
    return offer_id


def get_offer(offer_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, creator_id, creator_name, creator_username, gift_name, gift_link, price, status, expires_at
        FROM offers WHERE id = ?
        """,
        (offer_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0], "creator_id": row[1], "creator_name": row[2],
        "creator_username": row[3] or "", "gift_name": row[4], "gift_link": row[5],
        "price": row[6], "status": row[7], "expires_at": row[8],
    }


def update_offer_status(offer_id: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    accepted_at = datetime.now(timezone.utc).isoformat() if status == "accepted" else None
    c.execute("UPDATE offers SET status = ?, accepted_at = ? WHERE id = ?", (status, accepted_at, offer_id))
    conn.commit()
    conn.close()


# ================== ПАРСЕР ==================
LINK_RE = re.compile(r"(https?://(?:t\.me|telegram\.me)/nft/[A-Za-z0-9_\-]+)", re.IGNORECASE)
PRICE_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def parse_offer_text(text: str) -> Optional[Tuple[str, str, str]]:
    text = text.strip()
    text = re.sub(r"^!\s*прода[её]шь\??\s*", "", text, flags=re.IGNORECASE).strip()
    link_match = LINK_RE.search(text)
    if not link_match:
        return None
    gift_link = link_match.group(1)
    remaining = (text[:link_match.start()] + " " + text[link_match.end():]).strip()
    price_matches = list(PRICE_RE.finditer(remaining))
    if not price_matches:
        return None
    prices = [(float(m.group(1).replace(",", ".")), m) for m in price_matches]
    prices.sort(key=lambda x: x[0], reverse=True)
    price = prices[0][1].group(1).replace(",", ".")
    name_part = text[:link_match.start()].strip()
    name_part = PRICE_RE.sub("", name_part).strip()
    name_part = re.sub(r"\s+", " ", name_part).strip(" -–—!?")
    if name_part and len(name_part) > 1:
        gift_name = name_part
    else:
        slug = gift_link.rstrip("/").split("/")[-1]
        if "-" in slug:
            base, num = slug.rsplit("-", 1)
            if num.isdigit():
                nice = re.sub(r"([a-z])([A-Z])", r"\1 \2", base)
                gift_name = f"{nice} #{num}"
            else:
                gift_name = slug
        else:
            gift_name = slug
    return gift_name, gift_link, price


def format_remaining(expires_at: Optional[str]) -> str:
    if not expires_at:
        return f"{OFFER_TTL_HOURS} ч. 0 мин."
    try:
        exp = datetime.fromisoformat(expires_at)
        now = datetime.now(timezone.utc)
        if exp <= now:
            return "0 ч. 0 мин."
        delta = exp - now
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"{hours} ч. {minutes} мин."
    except Exception:
        return f"{OFFER_TTL_HOURS} ч. 0 мин."


# ================== ТЕКСТЫ ==================
def make_offer_text(creator_name: str, price: str, gift_name: str, gift_link: str, expires_at: Optional[str] = None) -> str:
    remaining = format_remaining(expires_at)
    star = '<tg-emoji emoji-id="5897792062291449826">⭐</tg-emoji>'
    return (
        f"Пользователь <b>{creator_name}</b> предлагает Вам\n"
        f"<b>{price}</b> {star} за подарок <a href=\"{gift_link}\"><b>{gift_name}</b></a>.\n\n"
        f"Оффер действителен ещё {remaining}."
    )


def make_accepted_text(
    gift_name: str,
    buyer_name: str,
    price: str,
    gift_link: str
) -> str:
    star = pe(EMOJI["star"], "⭐")
    gift_e = '<tg-emoji emoji-id="6037175527846975726">🎁</tg-emoji>'

    return (
        f'{gift_e} Подарок: <a href="{gift_link}"><b>{gift_name}</b></a> успешно продан!\n\n'
        f'Передайте подарок покупателю <b>{buyer_name}</b> для зачисления <b>{price}</b> {star}'
    )

START_MANUAL = f"""{pe(EMOJI['instruction'], '📘')} <b>Инструкция по настройке</b>

▢ <b>Шаг 1. Выберите режим работы</b>
Обычный чат с ботом, кнопки и предложения доступны без Telegram Premium. Для подключения бота непосредственно к личным чатам через Telegram Business могут действовать требования Telegram к аккаунту.

{pe(EMOJI['step2'], '⭐')} <b>Шаг 2. Подключите бота к Telegram Business</b>
1. Откройте Настройки → Telegram Business
2. Перейдите в раздел Chat Bots
3. Добавьте нашего бота в свой аккаунт

{pe(EMOJI['gear'], '⚙️')} <b>Шаг 3. Выдайте все 5 разрешений «Manage Messages»</b>
При подключении бота включите все разрешения в категории «Manage Messages»:
• Удаление сообщений
• Редактирование сообщений
• Закрепление сообщений
• Управление чатом
• Другие действия с сообщениями

{pe(EMOJI['important'], '⚠️')} <b>Важно</b>
Без этих разрешений бот может не получить сообщения из личных бизнес-чатов.

{pe(EMOJI['step4'], '✨')} <b>Шаг 4. Создайте предложение</b>
Отправьте одну команду:
<code>!продаёшь? &lt;ссылка&gt; &lt;сумма&gt; &lt;язык&gt;</code>

Пример:
<code>!продаёшь? https://t.me/nft/Gift-123 100 ru</code>

{pe(EMOJI['explanation'], '⚡')} <b>Пояснения</b>
Цена указывается в Telegram Stars.
Языки: ru — русский, en — английский, zh — китайский, ar — арабский.

<tg-emoji emoji-id="5217881018299595934">❗️</tg-emoji> Если возникли вопросы — напишите в поддержку.

——————————————
<b>Подписки:</b>
• <b>Normal</b> — обычная подписка для создания офферов
• <b>VIP</b> — лучшая подписка для офферов
"""


OWNER_TEXT = (
    f"<tg-emoji emoji-id=\"6271387924223234127\">👑</tg-emoji> <b>Владелец данного Telegram-бота</b>\n\n"
    f"@{OWNER_USERNAME}\n\n"
    f"Все вопросы и ошибки — в личные сообщения.\n"
    f"По вопросам подписки тоже пишите сюда."
)


# ================== КЛАВИАТУРЫ ==================
def offer_keyboard(offer_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Отклонить", callback_data=f"reject:{offer_id}", icon_custom_emoji_id="5985346521103604145"),
            InlineKeyboardButton("Принять", callback_data=f"accept:{offer_id}", icon_custom_emoji_id="5985596818912712352"),
        ]
    ])


def accepted_keyboard(offer_id: int, creator_id: int, creator_username: str) -> InlineKeyboardMarkup:
    # Deep link attempt
    deep = f"tg://send_gift?to={creator_id}"
    buttons = [
        [
            InlineKeyboardButton("Передать NFT", url=deep if creator_id else f"https://t.me/{creator_username.lstrip('@')}", icon_custom_emoji_id="6037175527846975726"),
            InlineKeyboardButton("❓ Как передать?", callback_data=f"how:{offer_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def start_keyboard(subscribed: bool = False, is_vip: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if not subscribed:
        buttons.append([InlineKeyboardButton("✅ Подписаться на канал", url=f"https://t.me/{SUB_CHANNEL}")])
        buttons.append([InlineKeyboardButton("🔄 Я подписался", callback_data="check_sub")])
    buttons.append([
        InlineKeyboardButton("Приобрести подписку", callback_data="buy_sub"),
        InlineKeyboardButton("Владелец", callback_data="owner_info"),
    ])
    return InlineKeyboardMarkup(buttons)


def buy_sub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Normal — 200 ⭐", url=f"https://t.me/{OWNER_USERNAME}?text=Хочу%20купить%20подписку%20Normal%20за%20200%20звёзд"),
            InlineKeyboardButton("VIP — 400 ⭐", url=f"https://t.me/{OWNER_USERNAME}?text=Хочу%20купить%20подписку%20VIP%20за%20400%20звёзд"),
        ]
    ])


def owner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Написать владельцу", url=f"https://t.me/{OWNER_USERNAME}")]])


# ================== ПРОВЕРКА ПОДПИСКИ ==================
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{SUB_CHANNEL}", user_id=user_id)
        return member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED)
    except TelegramError:
        return False


# ================== ЗАЩИТА (простая) ==================
# Случайные небольшие задержки для снижения риска флуда
async def safe_delay():
    await asyncio.sleep(random.uniform(0.3, 1.1))


# ================== ХЕНДЛЕРЫ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    await safe_delay()

    subscribed = await check_subscription(user.id, context)
    allowed = is_allowed(user.id)
    is_vip = get_sub_type(user.id) == "vip" if allowed else False

    if not subscribed:
        caption = (
            "🔒 <b>Для использования бота необходимо подписаться на канал</b>\n\n"
            f"👉 https://t.me/{SUB_CHANNEL}\n\n"
            "После подписки нажмите кнопку <b>«Я подписался»</b>."
        )
        try:
            with open(WELCOME_PHOTO, "rb") as photo:
                await update.message.reply_photo(photo=InputFile(photo), caption=caption, parse_mode=ParseMode.HTML, reply_markup=start_keyboard(False))
        except FileNotFoundError:
            await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=start_keyboard(False))
        return

    if not allowed:
        text = f"Для использования бота приобретите подписку у владельца.\n\nВладелец: @{OWNER_USERNAME}"
        try:
            with open(WELCOME_PHOTO, "rb") as photo:
                await update.message.reply_photo(photo=InputFile(photo), caption=text, parse_mode=ParseMode.HTML, reply_markup=start_keyboard(True))
        except FileNotFoundError:
            await update.message.reply_text(text, reply_markup=start_keyboard(True))
        return

    # Обычный мануал для пользователей с доступом
    await update.message.reply_text(
        START_MANUAL,
        parse_mode=ParseMode.HTML,
        reply_markup=start_keyboard(True, is_vip),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def meowner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    grant_access(user.id, user.username, user.first_name, days=0, sub_type="vip")
    await update.message.reply_text(f"{pe(EMOJI['check'], '✅')} Доступ открыт господин! (VIP бессрочно)", parse_mode=ParseMode.HTML)


async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_allowed(user.id):
        await update.message.reply_text("Нет доступа.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Использование:\n<code>/grant user_id дней [normal|vip]</code>\n\n"
            "Примеры:\n<code>/grant 123456789 30 normal</code>\n"
            "<code>/grant 123456789 30 vip</code>\n"
            "0 дней = бессрочно",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        target_id = int(args[0])
        days = int(args[1])
        sub_type = args[2].lower() if len(args) > 2 else "normal"
        if sub_type not in ("normal", "vip"):
            sub_type = "normal"
    except ValueError:
        await update.message.reply_text("user_id и days должны быть числами.")
        return

    grant_access(target_id, None, None, days=days, sub_type=sub_type)
    check = pe(EMOJI["check"], "✅")
    if days > 0:
        await update.message.reply_text(
            f"{check} Пользователю <code>{target_id}</code> выдана подписка <b>{sub_type.upper()}</b> на <b>{days}</b> дней.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"{check} Пользователю <code>{target_id}</code> выдан бессрочный доступ <b>{sub_type.upper()}</b>.",
            parse_mode=ParseMode.HTML,
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message
    if not user or not message or not message.text:
        return

    await safe_delay()

    if not await check_subscription(user.id, context):
        await message.reply_text(
            f"🔒 Сначала подпишитесь на канал https://t.me/{SUB_CHANNEL}\nПосле подписки нажмите /start",
            reply_markup=start_keyboard(False),
        )
        return

    if not is_allowed(user.id):
        await message.reply_text(
            "Для использования приобретите подписку у владельца.",
            reply_markup=start_keyboard(True),
        )
        return

    text = message.text.strip()

    if re.match(r"^!\s*прода[её]шь", text, re.IGNORECASE) or LINK_RE.search(text):
        parsed = parse_offer_text(text)
        if not parsed:
            await message.reply_text(
                "Не удалось распознать оффер.\nФормат:\n<code>!продаёшь? https://t.me/nft/Name-123 15000 ru</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        gift_name, gift_link, price = parsed
        creator_name = user.first_name or user.username or "Пользователь"
        creator_username = user.username or ""

        offer_id = create_offer(user.id, creator_name, creator_username, gift_name, gift_link, price)
        offer = get_offer(offer_id)
        text_msg = make_offer_text(creator_name, price, gift_name, gift_link, offer["expires_at"] if offer else None)

        await message.reply_text(
            text_msg,
            reply_markup=offer_keyboard(offer_id),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True),
        )
        return

    if not text.startswith("/"):
        await message.reply_text(
            "Отправьте оффер в формате:\n<code>!продаёшь? https://t.me/nft/... 15000 ru</code>",
            parse_mode=ParseMode.HTML,
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    user = query.from_user
    await safe_delay()

    if data == "check_sub":
        await query.answer()
        subscribed = await check_subscription(user.id, context)
        if subscribed:
            try:
                await query.edit_message_caption(caption="✅ Подписка подтверждена!\nНажмите /start ещё раз.", reply_markup=None)
            except Exception:
                await query.edit_message_text("✅ Подписка подтверждена!\nНажмите /start ещё раз.")
        else:
            await query.answer("Вы ещё не подписаны на канал.", show_alert=True)
        return

    if data == "buy_sub":
        await query.answer()
        await query.message.reply_text(
            "Выберите тип подписки:",
            reply_markup=buy_sub_keyboard(),
        )
        return

    if data == "owner_info":
        await query.answer()
        try:
            with open(OWNER_PHOTO, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=InputFile(photo),
                    caption=OWNER_TEXT,
                    parse_mode=ParseMode.HTML,
                    reply_markup=owner_keyboard(),
                )
        except FileNotFoundError:
            await context.bot.send_message(chat_id=query.message.chat_id, text=OWNER_TEXT, parse_mode=ParseMode.HTML, reply_markup=owner_keyboard())
        return


    if ":" not in data:
        return

    action, offer_id_str = data.split(":", 1)
    try:
        offer_id = int(offer_id_str)
    except ValueError:
        return

    offer = get_offer(offer_id)
    if not offer:
        await query.edit_message_text("Оффер не найден.")
        return

    if action == "reject":
        if offer["status"] != "pending":
            await query.answer("Оффер уже обработан.", show_alert=True)
            return
        await query.answer()
        update_offer_status(offer_id, "rejected")
        await query.edit_message_text('<tg-emoji emoji-id="5985346521103604145">❌</tg-emoji> Оффер отклонён.', parse_mode=ParseMode.HTML)

    elif action == "accept":
        if offer["status"] != "pending":
            await query.answer("Оффер уже обработан.", show_alert=True)
            return
        # Предупреждение как на фото 4
        await query.answer(
            "Внимание!\n\nСледуйте инструкциям, чтобы не потерять подарок и получить оплату.\n\nНажмите OK, если вы прочитали предупреждение.",
            show_alert=True,
        )
        update_offer_status(offer_id, "accepted")
        text = make_accepted_text(
            offer["gift_name"],
            offer["creator_name"],
            offer["price"],
            offer["gift_link"]
        )
        await query.edit_message_text(
            text,
            reply_markup=accepted_keyboard(
                offer_id,
                offer["creator_id"],
                offer.get("creator_username", "")
            ),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                show_above_text=True
            )
)

    elif action == "how":
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "❓ <b>Как передать коллекционный подарок</b>\n\n"
                "1. Откройте свой профиль → вкладка «Подарки».\n"
                "2. Выберите нужный подарок.\n"
                "3. Нажмите «Передать» / Transfer.\n"
                "4. Выберите получателя.\n"
                "5. Подтвердите.\n\n"
                "⚠️ Только коллекционные (upgraded) подарки."
            ),
            parse_mode=ParseMode.HTML,
            reply_to_message_id=query.message.message_id,
        )


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query
    if not query:
        return

    user = query.from_user
    text = (query.query or "").strip()

    try:
        subscribed = await check_subscription(user.id, context)
        allowed = is_allowed(user.id)

        if not subscribed or not allowed:
            await query.answer(
                [
                    InlineQueryResultArticle(
                        id=str(uuid4()),
                        title="Нет доступа",
                        description="Напишите боту /start",
                        input_message_content=InputTextMessageContent("Нет доступа. Напишите боту /start"),
                    )
                ],
                cache_time=5,
            )
            return

        if not text:
            await query.answer(
                [
                    InlineQueryResultArticle(
                        id=str(uuid4()),
                        title="Введите ссылку и цену",
                        description="Пример: https://t.me/nft/Name-123 50",
                        input_message_content=InputTextMessageContent("Отправьте ссылку на NFT и цену"),
                    )
                ],
                cache_time=3,
            )
            return

        parsed = parse_offer_text(text)
        if not parsed:
            await query.answer(
                [
                    InlineQueryResultArticle(
                        id=str(uuid4()),
                        title="Неверный формат",
                        description="Нужно: ссылка + цена",
                        input_message_content=InputTextMessageContent("Формат: https://t.me/nft/Name-123 50"),
                    )
                ],
                cache_time=3,
            )
            return

        gift_name, gift_link, price = parsed
        creator_name = user.first_name or user.username or "Пользователь"
        creator_username = user.username or ""

        offer_id = create_offer(user.id, creator_name, creator_username, gift_name, gift_link, price)
        offer = get_offer(offer_id)
        offer_text = make_offer_text(creator_name, price, gift_name, gift_link, offer["expires_at"] if offer else None)

        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"{gift_name} — {price} Stars",
                description=f"Оффер от {creator_name}",
                input_message_content=InputTextMessageContent(
                    offer_text,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True),
                ),
                reply_markup=offer_keyboard(offer_id),
            )
        ]
        await query.answer(results, cache_time=3)

    except Exception as e:
        logger.error(f"Inline error: {e}", exc_info=True)
        try:
            await query.answer(
                [
                    InlineQueryResultArticle(
                        id=str(uuid4()),
                        title="Ошибка",
                        description="Попробуйте ещё раз",
                        input_message_content=InputTextMessageContent("Произошла ошибка"),
                    )
                ],
                cache_time=1,
            )
        except Exception:
            pass


def main() -> None:
    if not BOT_TOKEN:
        print("ОШИБКА: Укажите BOT_TOKEN!")
        return

    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler(OWNER_SECRET, meowner))
    application.add_handler(CommandHandler("grant", grant_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
