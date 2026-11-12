# Offer TG

A Telegram bot for creating and managing collectible-gift offers. Version 2 focuses on offer safety, a native-feeling Telegram chat interface, and preserving the original SQLite data.

## Product boundary

Offer TG creates and tracks a third-party offer only. The amount shown in Stars is an advertised price. The bot does not debit, escrow, reserve, refund, or transfer Stars, and it does not transfer Telegram gifts. The buyer and seller complete payment and gift transfer separately. An accepted status means only that a user pressed Accept.

Telegram's official gift-purchase offer is a Telegram-generated service message. Its `payments.sendStarGiftOffer` method is a user-only MTProto method, not a Bot API method. This bot therefore renders an explicitly branded "Offer TG" message with a clear third-party disclaimer; it does not pretend to create Telegram's official centered service message. See the [official Telegram Gifts API](https://core.telegram.org/api/gifts), [sendStarGiftOffer method](https://core.telegram.org/method/payments.sendStarGiftOffer), and [Telegram's anti-scam guidance](https://www.t.me/s/FAQTelegram/3126?q=%23scam).

Native Telegram gift-purchase offers and escrow are explicitly out of scope for this release.

## Features

- Compact Offer TG-branded offer message with a gift-link preview and custom-emoji Accept / Decline buttons (with a plain-button fallback if Telegram rejects custom icons).
- Public offers, or offers addressed to a specific user by replying to that person's message in a group.
- Creator-only cancellation; the creator cannot accept or decline their own offer.
- Atomic status transitions, expiry checks, and audit events.
- SQLite WAL mode and additive migrations from the original bot schema.
- Existing users and offers are preserved.
- Admin-only grant, revoke, and statistics commands.
- Configurable daily offer limits for Normal and VIP.
- RU, EN, Chinese, and Arabic offer cards and action buttons.
- Telegram Business offer delivery from the connected profile to eligible private chats, selected from recent incoming conversations.
- Telegram Business connection state and recent contacts are persisted; disabled connections, missing reply rights, expired contact activity, and unauthorized recipient selections are rejected.
- Inline query offer creation remains available as a fallback.
- Telegram Business message replies and edits use the stored business connection ID.
- .env is loaded explicitly from the project root; process environment variables override it.
- Docker image and Compose deployment files.
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
4. The app loads .env from the repository root before reading settings, even when launched from another working directory. Existing environment variables (for example Docker/systemd variables) take precedence over .env.
5. Keep DB_PATH=offers.db if the existing deployment uses the legacy offers.db file.
6. Start the application:

       python "bot3 (1).py"

The legacy filename remains as a compatibility launcher. The new implementation lives in offerbot/.

### Docker Compose

For a new installation:

    cp .env.example .env
    # edit .env: set BOT_TOKEN and OWNER_ID
    mkdir -p data
    sudo chown -R 10001:10001 data
    docker compose up -d --build

SQLite is persisted in ./data/offers.db. For an existing deployment, stop the old bot first, copy its actual database and set permissions before the first V2 start:

    cp /path/to/current/offers.db data/offers.db
    sudo chown 10001:10001 data/offers.db
    docker compose up -d --build

The container runs as a non-root user (UID 10001). Never run two bot processes against the same database and token at the same time.

## Environment variables

| Variable | Required | Description |
|---|---:|---|
| BOT_TOKEN | Yes | Fresh Telegram bot token; loaded from the project-root .env or process environment; never put it in source control |
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

In a group, reply to a person's message with the offer command to address the offer to that person. Otherwise the offer is open to everyone except its creator. To let the bot see custom text messages in groups, disable BotFather Privacy Mode for the bot or grant it the required group permissions.

### Send an offer from your Telegram Business profile

Business delivery is the primary workflow when you want the offer to appear as a message from your connected personal profile.

1. In @BotFather, enable Business Mode for the bot if that option is available.
2. In Telegram, open **Settings → Telegram Business → Chatbots**, connect Offer TG, and grant the permission to reply to messages.
3. A recipient must have recently messaged your business profile in a private chat. Telegram only allows business replies to chats covered by the connection permissions and recent-activity rules; the bot cannot search arbitrary Telegram users or message any username at will.
4. Open the regular private chat with Offer TG (not the business-profile conversation) and run:
   `/businessoffer https://t.me/nft/Gift-123 100 ru`
5. Choose a recipient from the list of recent private chats the connected profile is permitted to reply to. The bot sends the offer on behalf of your profile and stores the message and connection IDs so that the buttons, expiry and status updates can be processed.

The recipient list is built only from private incoming messages received while the connection is active and has reply permission. A contact disappears from the selectable list after 24 hours without new incoming activity. If Telegram rejects a send because the connection or chat is no longer eligible, the offer is marked cancelled and the bot reports the limitation. The bot does not send to arbitrary groups through this workflow.

Custom button icons are attempted on the business message, with standard neutral buttons used only if Telegram rejects the custom icons. Whether custom icons render must be verified in the real Telegram client; Business mode alone does not guarantee it.

### Inline fallback

Inline mode remains available for sending bot-authored offer cards to chats where Business delivery is unavailable:

1. Enable inline mode in @BotFather with `/setinline`.
2. Type `@BOT_USERNAME https://t.me/nft/Gift-123 100 ru` in the target chat.
3. Select the Offer TG result.

Inline results are sent as bot messages, not as messages from your connected personal profile. Do not forward an existing card because Telegram may remove its inline keyboard.

## Commands

- /start — open the menu
- /help — usage and safety notes
- /myoffers — recent offers created by you, addressed to you, or resolved by you
- /canceloffer OFFER_ID — cancel your own pending offer
- /businessoffer NFT_LINK PRICE [LANG] — choose a recent eligible private chat and send the offer from your connected Telegram Business profile
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
