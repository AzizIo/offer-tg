# Offer TG

A Telegram bot for creating and managing collectible-gift offers. Version 2 focuses on offer safety, a native-feeling Telegram chat interface, and preserving the original SQLite data.

## Product boundary

Offer TG creates and tracks an offer only. The amount shown in Stars is an advertised price. The bot does not debit, escrow, reserve, refund, or transfer Stars, and it does not transfer Telegram gifts. The buyer and seller complete payment and gift transfer separately. An accepted status means only that a user pressed Accept.

Native Telegram gift-purchase offers and escrow are explicitly out of scope for this release.

## Features

- Telegram-style offer message with Premium emoji and Accept / Decline actions.
- Public offers, or offers addressed to a specific user by replying to that person's message in a group.
- Creator-only cancellation; the creator cannot accept or decline their own offer.
- Atomic status transitions, expiry checks, and audit events.
- SQLite WAL mode and additive migrations from the original bot schema.
- Existing users and offers are preserved.
- Admin-only grant, revoke, and statistics commands.
- Configurable daily offer limits for Normal and VIP.
- RU, EN, Chinese, and Arabic offer cards and action buttons.
- Inline query offer creation.
- Telegram Business message replies and edits use the stored business connection ID.
- Automated tests and GitHub Actions.

## Requirements

- Python 3.11+
- A Telegram bot token from @BotFather
- Numeric Telegram user ID for the product owner
- The bot must be an administrator in the subscription channel if channel gating is enabled.

## Setup

1. Revoke any bot token that was ever committed to the repository or shared in chat. Generate a new token with @BotFather.
2. Create a virtual environment and install dependencies:

       python3 -m venv .venv
       source .venv/bin/activate
       python -m pip install -e ".[dev]"

3. Copy .env.example to .env and configure at least BOT_TOKEN and OWNER_ID.
4. Keep DB_PATH=offers.db if the existing deployment uses the legacy offers.db file.
5. Start the application:

       python "bot3 (1).py"

The legacy filename remains as a compatibility launcher. The new implementation lives in offerbot/.

## Environment variables

| Variable | Required | Description |
|---|---:|---|
| BOT_TOKEN | Yes | Fresh Telegram bot token; never put it in source control |
| OWNER_ID | Yes | Numeric Telegram ID of the product owner |
| OWNER_USERNAME | No | Public support username used in menu links |
| ADMIN_IDS | No | Comma-separated trusted admin IDs |
| SUB_CHANNEL | No | Public channel username; empty disables membership gate |
| DB_PATH | No | SQLite path; defaults to the legacy-compatible offers.db |
| DEFAULT_OFFER_TTL_HOURS | No | 1, 3, 6, 12, 24, 48, or 72 |
| NORMAL_DAILY_OFFERS | No | Normal daily creation quota |
| VIP_DAILY_OFFERS | No | VIP daily creation quota |
| NORMAL_PRICE_STARS | No | Informational subscription price |
| VIP_PRICE_STARS | No | Informational subscription price |

## Offer syntax

    !продаёшь? https://t.me/nft/Gift-123 100 ru

The price must be a positive whole number of Stars. Supported language codes are ru, en, zh, and ar. The message catalog includes Russian, English, Chinese, and Arabic.

In a group, reply to a person's message with the offer command to address the offer to that person. Otherwise the offer is open to everyone except its creator.

## Commands

- /start — open the menu
- /help — usage and safety notes
- /myoffers — recent offers created by or addressed to you
- /grant USER_ID DAYS [normal|vip] — admin-only subscription grant; zero days means unlimited
- /revoke USER_ID — admin-only subscription revocation
- /stats — admin-only summary

Only OWNER_ID and ADMIN_IDS may manage subscriptions. The old secret command has been removed.

## Database migration

The first V2 startup adds missing columns and creates an audit table. It does not drop or recreate the original allowed_users or offers tables. Back up the SQLite database before the first V2 deployment anyway.

The original bot used offers.db. V2 defaults to that same path, so the first startup in the same working directory can migrate existing users and offers. If the database lives elsewhere, set DB_PATH to its exact existing path before starting V2.

## Tests

    pytest
    python -m compileall -q offerbot "bot3 (1).py"

## Roadmap

1. Complete security and offer-state hardening.
2. Run end-to-end UX tests in private chats, groups, inline mode, and Telegram Business connections.
3. Build a real admin interface and subscription checkout.
4. Add operational monitoring, backups, and deployment automation.
5. Evaluate native Telegram gift offers as a separate future integration.
