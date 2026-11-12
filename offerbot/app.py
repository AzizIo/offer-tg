from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    LinkPreviewOptions,
    Update,
    BotCommand,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import TelegramError, Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from .config import ConfigurationError, Settings
from .keyboards import offer_keyboard, start_keyboard
from .parser import parse_offer_text
from .presentation import make_offer_text, make_resolved_text, tr
from .storage import (
    OfferAlreadyResolved,
    OfferExpired,
    OfferLimitReached,
    OfferNotFound,
    OfferPermissionDenied,
    Storage,
)


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("offerbot")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_environment(env_file: Path | None = None) -> bool:
    """Load the project .env regardless of the shell's current directory.

    Existing process environment variables take precedence, which is useful
    for Docker, systemd, and managed deployment environments.
    """
    dotenv_path = env_file or PROJECT_ROOT / ".env"
    return load_dotenv(dotenv_path=dotenv_path, override=False)


def get_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


def get_storage(context: ContextTypes.DEFAULT_TYPE) -> Storage:
    return context.application.bot_data["storage"]


async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings = get_settings(context)
    if not settings.sub_channel:
        return True
    try:
        member = await context.bot.get_chat_member(
            chat_id=f"@{settings.sub_channel}",
            user_id=user_id,
        )
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        } or (member.status == ChatMemberStatus.RESTRICTED and bool(getattr(member, "is_member", False)))
    except TelegramError:
        logger.warning("Could not verify channel membership for user_id=%s", user_id)
        return False


async def user_can_create(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings = get_settings(context)
    if settings.is_admin(user_id):
        return True
    if not await check_subscription(user_id, context):
        return False
    return get_storage(context).is_allowed(user_id)


def is_group_chat(update: Update) -> bool:
    message = update.effective_message
    return bool(message and message.chat and message.chat.type in {"group", "supergroup"})


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    settings = get_settings(context)
    storage = get_storage(context)
    if settings.is_admin(user.id):
        text = (
            "👑 <b>Offer TG V2</b>\n\n"
            "Панель владельца доступна.\n"
            "Команды: /stats, /grant, /revoke, /myoffers, /help."
        )
        await message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard(os.getenv("OWNER_USERNAME", "RuslanArasov")),
        )
        return

    subscribed = await check_subscription(user.id, context)
    if not subscribed:
        await message.reply_text(
            "🔒 <b>Для использования сервиса подпишитесь на канал.</b>\n\n"
            f"https://t.me/{settings.sub_channel}\n\nПосле подписки нажмите «Проверить подписку».",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Проверить подписку", callback_data="subscription:check")
            ]]),
        )
        return

    access = storage.get_access(user.id)
    if not access:
        await message.reply_text(
            "Добро пожаловать в <b>Offer TG</b>.\n\n"
            "Создание офферов доступно по подписке. Выберите тариф или напишите владельцу.\n"
            "Пользователи, которым вы адресовали предложение, могут принять или отклонить его без платной подписки.",
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard(os.getenv("OWNER_USERNAME", "RuslanArasov")),
        )
        return

    plan = str(access.get("sub_type") or "normal").upper()
    await message.reply_text(
        f"👋 Добро пожаловать в <b>Offer TG</b>!\n\n"
        f"Ваша подписка: <b>{plan}</b>\n\n"
        "Создайте предложение сообщением:\n"
        "<code>!продаёшь? https://t.me/nft/Gift-123 100 ru</code>\n\n"
        "Можно ответить этой командой на сообщение покупателя в группе — тогда оффер будет адресован именно ему.\n"
        "В остальных случаях это открытый оффер: принять его может любой пользователь, кроме автора.\n\n"
        "Бот не списывает и не резервирует Stars. Передача подарка и расчёт происходят отдельно.",
        parse_mode=ParseMode.HTML,
        reply_markup=start_keyboard(os.getenv("OWNER_USERNAME", "RuslanArasov")),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    await message.reply_text(
        "📘 <b>Как пользоваться Offer TG</b>\n\n"
        "<b>Создание:</b>\n"
        "<code>!продаёшь? https://t.me/nft/Gift-123 100 ru</code>\n\n"
        "Цена — целое число Telegram Stars. Поддерживаются языки ru, en, zh, ar.\n"
        "Чтобы адресовать оффер конкретному человеку в группе, ответьте командой на его сообщение.\n\n"
        "<b>Управление:</b>\n"
        "Автор может отменить свой оффер командой /canceloffer ID (ID доступен в /myoffers). "
        "Другой пользователь может принять или отклонить оффер. Автор не может принять собственный оффер.\n\n"
        "<b>Важно:</b> Offer TG не резервирует Stars, не проверяет факт передачи NFT и не выступает гарантом сделки.",
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    settings = get_settings(context)
    if not settings.is_admin(user.id):
        await message.reply_text("Нет прав. Команда доступна только владельцу и администраторам.")
        return
    if len(context.args) < 2:
        await message.reply_text(
            "Использование:\n/grant USER_ID DAYS [normal|vip]\n"
            "Пример: /grant 123456789 30 vip\n0 дней = бессрочно"
        )
        return
    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
        plan = context.args[2].lower() if len(context.args) > 2 else "normal"
        if plan not in {"normal", "vip"}:
            raise ValueError
        if target_id <= 0 or days < 0:
            raise ValueError
    except ValueError:
        await message.reply_text("Проверьте USER_ID, количество дней и тип подписки.")
        return
    get_storage(context).grant_access(
        target_id,
        username=None,
        first_name=None,
        days=days,
        plan=plan,
        actor_id=user.id,
    )
    await message.reply_text(
        f"✅ Пользователю <code>{target_id}</code> выдана подписка <b>{plan.upper()}</b> на "
        f"<b>{'бессрочно' if days == 0 else f'{days} дн.'}</b>.",
        parse_mode=ParseMode.HTML,
    )


async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    if not get_settings(context).is_admin(user.id):
        await message.reply_text("Нет прав. Команда доступна только владельцу и администраторам.")
        return
    if len(context.args) != 1:
        await message.reply_text("Использование: /revoke USER_ID")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await message.reply_text("USER_ID должен быть числом.")
        return
    revoked = get_storage(context).revoke_access(target_id, actor_id=user.id)
    await message.reply_text("✅ Подписка отозвана." if revoked else "У пользователя нет активной записи подписки.")


async def cancel_offer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    if len(context.args) != 1:
        await message.reply_text("Использование: /canceloffer OFFER_ID")
        return
    try:
        offer_id = int(context.args[0])
        if offer_id <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("OFFER_ID должен быть положительным числом.")
        return

    storage = get_storage(context)
    try:
        offer = storage.resolve_offer(offer_id, actor_id=user.id, action="cancelled")
    except OfferNotFound:
        await message.reply_text("Оффер не найден.")
        return
    except OfferAlreadyResolved:
        await message.reply_text("Оффер уже обработан.")
        return
    except OfferExpired:
        await message.reply_text("Срок действия оффера уже истёк.")
        return
    except OfferPermissionDenied:
        await message.reply_text("Отменить оффер может только его автор.")
        return

    result_text = make_resolved_text(offer, "cancelled", user.full_name or str(user.id))
    chat_id = offer.get("source_chat_id")
    source_message_id = offer.get("source_message_id")
    if chat_id and source_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=int(chat_id),
                message_id=int(source_message_id),
                business_connection_id=offer.get("source_business_connection_id"),
                text=result_text,
                parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=False),
            )
        except TelegramError:
            logger.info("Could not edit cancelled offer message id=%s", offer_id)
    await message.reply_text("✅ Оффер отменён.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    if not get_settings(context).is_admin(user.id):
        await message.reply_text("Нет прав.")
        return
    stats = get_storage(context).stats()
    await message.reply_text(
        "📊 <b>Offer TG — статистика</b>\n\n"
        f"Подписки в базе: <b>{stats['users']}</b>\n"
        f"Всего офферов: <b>{stats['offers']}</b>\n"
        f"Ожидают: <b>{stats['pending']}</b>\n"
        f"Приняты: <b>{stats['accepted']}</b>\n"
        f"Истекли: <b>{stats['expired']}</b>",
        parse_mode=ParseMode.HTML,
    )


async def my_offers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    rows = get_storage(context).list_user_offers(user.id, limit=10)
    if not rows:
        await message.reply_text("У вас пока нет офферов.")
        return
    labels = {
        "pending": "ожидает",
        "accepted": "принят",
        "rejected": "отклонён",
        "cancelled": "отменён",
        "expired": "истёк",
    }
    from html import escape
    lines = ["<b>Последние предложения</b>\n"]
    for row in rows:
        lines.append(
            f"#{row['id']} · <b>{escape(str(row['gift_name']))}</b> · {escape(str(row['price']))} ⭐\n"
            f"Статус: {labels.get(row['status'], row['status'])}"
        )
    await message.reply_text("\n\n".join(lines), parse_mode=ParseMode.HTML)


async def create_offer_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message or not message.text:
        return

    parsed = parse_offer_text(message.text)
    if not parsed:
        if message.text.lstrip().startswith("!") or "t.me/nft/" in message.text.lower():
            await message.reply_text(
                "Не удалось распознать предложение.\nФормат:\n"
                "<code>!продаёшь? https://t.me/nft/Gift-123 100 ru</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    settings = get_settings(context)
    if not await user_can_create(user.id, context):
        await message.reply_text(
            "Для создания офферов нужна активная подписка и, если включено, подписка на канал.",
            reply_markup=start_keyboard(os.getenv("OWNER_USERNAME", "RuslanArasov")),
        )
        return

    recipient_id = None
    replied = message.reply_to_message
    if replied and replied.from_user and not replied.from_user.is_bot and replied.from_user.id != user.id:
        recipient_id = replied.from_user.id

    plan_access = get_storage(context).get_access(user.id)
    plan = str(plan_access.get("sub_type") if plan_access else "vip")
    daily_limit = settings.daily_limit(plan)
    try:
        offer_id = get_storage(context).create_offer(
            creator_id=user.id,
            creator_name=user.full_name or user.username or "Пользователь",
            creator_username=user.username or "",
            gift_name=parsed.gift_name,
            gift_link=parsed.gift_link,
            price_stars=parsed.price_stars,
            ttl_hours=settings.default_offer_ttl_hours,
            language=parsed.language,
            recipient_id=recipient_id,
            daily_limit=daily_limit,
        )
    except OfferLimitReached:
        await message.reply_text("Достигнут дневной лимит офферов для вашего тарифа.")
        return

    offer = get_storage(context).get_offer(offer_id)
    if not offer:
        await message.reply_text("Не удалось создать оффер. Попробуйте ещё раз.")
        return
    sent = await message.reply_text(
        make_offer_text(offer),
        reply_markup=offer_keyboard(offer_id, parsed.language),
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True),
    )
    get_storage(context).set_offer_message(
        offer_id,
        sent.chat_id,
        sent.message_id,
        business_connection_id=getattr(sent, "business_connection_id", None),
    )


async def notify_creator(context: ContextTypes.DEFAULT_TYPE, offer: dict, text: str) -> None:
    creator_id = int(offer["creator_id"])
    try:
        await context.bot.send_message(
            chat_id=creator_id,
            text=text,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except (Forbidden, TelegramError):
        logger.info("Could not send private notification to offer creator user_id=%s", creator_id)


async def edit_offer_message(query, text: str, reply_markup=None) -> None:
    if query.inline_message_id:
        await query.get_bot().edit_message_text(
            text=text,
            inline_message_id=query.inline_message_id,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            link_preview_options=LinkPreviewOptions(is_disabled=False),
        )
    elif query.message:
        business_connection_id = getattr(query.message, "business_connection_id", None)
        if business_connection_id:
            await query.get_bot().edit_message_text(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                business_connection_id=business_connection_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                link_preview_options=LinkPreviewOptions(is_disabled=False),
            )
        else:
            await query.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                link_preview_options=LinkPreviewOptions(is_disabled=False),
            )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    data = query.data
    user = query.from_user
    storage = get_storage(context)

    # Keep buttons already sent by the legacy version operational after migration.
    if data.startswith(("accept:", "reject:", "how:")):
        legacy_action, legacy_id = data.split(":", 1)
        action_alias = {"accept": "accept", "reject": "reject", "how": "how"}
        data = f"offer:{action_alias[legacy_action]}:{legacy_id}"

    if data == "menu:help":
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "📘 <b>Создание оффера</b>\n"
                "<code>!продаёшь? https://t.me/nft/Gift-123 100 ru</code>\n\n"
                "Ответьте этим сообщением на сообщение адресата, чтобы оффер был персональным.\n"
                "Без ответа оффер открыт для других пользователей. Автор не может принять свой оффер.\n\n"
                "Stars не резервируются и подарок автоматически не передаётся."
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "subscription:plans":
        settings = get_settings(context)
        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "💎 <b>Подписки Offer TG</b>\n\n"
                f"Normal — {os.getenv('NORMAL_PRICE_STARS', '200')} ⭐ / 30 дней\n"
                f"VIP — {os.getenv('VIP_PRICE_STARS', '400')} ⭐ / 30 дней\n\n"
                "Для оформления напишите владельцу. Автоматическую оплату подключим отдельным этапом."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=start_keyboard(os.getenv("OWNER_USERNAME", "RuslanArasov")),
        )
        return

    if data == "subscription:check":
        if await check_subscription(user.id, context):
            await query.answer("Подписка подтверждена. Нажмите /start.", show_alert=True)
        else:
            await query.answer("Подписка пока не найдена.", show_alert=True)
        return

    if data.startswith("offer:"):
        parts = data.split(":")
        if len(parts) != 3:
            await query.answer("Некорректная кнопка.", show_alert=True)
            return
        _, action, raw_id = parts
        try:
            offer_id = int(raw_id)
        except ValueError:
            await query.answer("Некорректный ID оффера.", show_alert=True)
            return

        if action == "how":
            offer = storage.get_offer(offer_id)
            language = str(offer.get("language") or "ru") if offer else "ru"
            await query.answer()
            await context.bot.send_message(
                chat_id=query.message.chat_id if query.message else user.id,
                business_connection_id=getattr(query.message, "business_connection_id", None) if query.message else None,
                text=tr(language, "how_text"),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=query.message.message_id if query.message else None,
            )
            return

        action_map = {
            "accept": "accepted",
            "reject": "rejected",
            "cancel": "cancelled",
        }
        db_action = action_map.get(action)
        if db_action is None:
            await query.answer("Неизвестное действие.", show_alert=True)
            return

        try:
            offer = storage.resolve_offer(offer_id, actor_id=user.id, action=db_action)
        except OfferNotFound:
            await query.answer("Оффер не найден.", show_alert=True)
            return
        except OfferAlreadyResolved:
            await query.answer("Оффер уже обработан.", show_alert=True)
            return
        except OfferExpired:
            await query.answer("Срок действия оффера истёк.", show_alert=True)
            latest = storage.get_offer(offer_id)
            if latest:
                await edit_offer_message(query, make_resolved_text(latest, "expired", ""))
            return
        except OfferPermissionDenied:
            await query.answer("У вас нет прав на это действие.", show_alert=True)
            return

        actor_name = user.full_name or user.username or str(user.id)
        text = make_resolved_text(offer, db_action, actor_name)
        await query.answer({
            "accepted": "Предложение принято.",
            "rejected": "Предложение отклонено.",
            "cancelled": "Оффер отменён.",
        }[db_action])
        await edit_offer_message(query, text)
        if user.id != int(offer["creator_id"]):
            await notify_creator(context, offer, text)
        return


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query
    if not query:
        return
    user = query.from_user
    if not await user_can_create(user.id, context):
        await query.answer([
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Нет доступа",
                description="Откройте бота и проверьте подписку",
                input_message_content=InputTextMessageContent("Нет доступа. Напишите боту /start."),
            )
        ], cache_time=2)
        return

    parsed = parse_offer_text(query.query or "")
    if not parsed:
        await query.answer([
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Введите ссылку и цену",
                description="https://t.me/nft/Gift-123 100 ru",
                input_message_content=InputTextMessageContent(
                    "Формат: https://t.me/nft/Gift-123 100 ru"
                ),
            )
        ], cache_time=2)
        return

    access = get_storage(context).get_access(user.id)
    plan = str(access.get("sub_type") if access else "vip")
    settings = get_settings(context)
    try:
        offer_id = get_storage(context).create_offer(
            creator_id=user.id,
            creator_name=user.full_name or user.username or "Пользователь",
            creator_username=user.username or "",
            gift_name=parsed.gift_name,
            gift_link=parsed.gift_link,
            price_stars=parsed.price_stars,
            ttl_hours=settings.default_offer_ttl_hours,
            language=parsed.language,
            daily_limit=settings.daily_limit(plan),
        )
    except OfferLimitReached:
        await query.answer([
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Достигнут дневной лимит",
                description="Попробуйте завтра",
                input_message_content=InputTextMessageContent("Достигнут дневной лимит офферов."),
            )
        ], cache_time=2)
        return

    offer = get_storage(context).get_offer(offer_id)
    if not offer:
        await query.answer([], cache_time=1)
        return
    await query.answer([
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"{parsed.gift_name} — {parsed.price_stars} Stars",
            description=f"Предложение от {user.full_name}",
            input_message_content=InputTextMessageContent(
                make_offer_text(offer),
                parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True),
            ),
            reply_markup=offer_keyboard(offer_id, parsed.language),
        )
    ], cache_time=1)


async def expire_offers_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    storage = get_storage(context)
    expired_ids = storage.expire_due_offers()
    for offer_id in expired_ids:
        offer = storage.get_offer(offer_id)
        if not offer:
            continue
        chat_id = offer.get("source_chat_id")
        message_id = offer.get("source_message_id")
        business_connection_id = offer.get("source_business_connection_id")
        if chat_id and message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=int(chat_id),
                    message_id=int(message_id),
                    business_connection_id=business_connection_id,
                    text=make_resolved_text(offer, "expired", ""),
                    parse_mode=ParseMode.HTML,
                    reply_markup=None,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            except TelegramError:
                logger.info("Could not edit expired offer message id=%s", offer_id)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled Telegram update error", exc_info=context.error)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("start", "Открыть меню"),
        BotCommand("help", "Инструкция"),
        BotCommand("myoffers", "Мои предложения"),
        BotCommand("canceloffer", "Отменить свой оффер"),
        BotCommand("stats", "Статистика (админ)"),
        BotCommand("grant", "Выдать подписку (админ)"),
        BotCommand("revoke", "Отозвать подписку (админ)"),
    ])
    if application.job_queue:
        application.job_queue.run_repeating(expire_offers_job, interval=60, first=30, name="expire-offers")


def main() -> None:
    try:
        # Load the repository-root .env before reading BOT_TOKEN and all other settings.
        load_environment()
        settings = Settings.from_env()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    storage = Storage(settings.db_path)
    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .build()
    )
    application.bot_data["settings"] = settings
    application.bot_data["storage"] = storage

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("grant", grant_command))
    application.add_handler(CommandHandler("revoke", revoke_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("myoffers", my_offers))
    application.add_handler(CommandHandler("canceloffer", cancel_offer_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, create_offer_from_message))
    application.add_error_handler(on_error)

    logger.info("Offer TG V2 starting; database=%s", settings.db_path)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
