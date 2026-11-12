from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


def _required_id(name: str) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a numeric Telegram user ID") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    owner_id: int
    admin_ids: frozenset[int]
    sub_channel: str
    db_path: Path
    default_offer_ttl_hours: int
    normal_daily_offers: int
    vip_daily_offers: int

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise ConfigurationError("BOT_TOKEN is required. Never hard-code it in source code.")

        owner_id = _required_id("OWNER_ID")
        admin_ids: set[int] = set()
        for raw in os.getenv("ADMIN_IDS", "").split(","):
            raw = raw.strip()
            if raw:
                try:
                    admin_id = int(raw)
                except ValueError as exc:
                    raise ConfigurationError("ADMIN_IDS must contain comma-separated numeric IDs") from exc
                if admin_id <= 0:
                    raise ConfigurationError("ADMIN_IDS must contain positive Telegram IDs")
                admin_ids.add(admin_id)

        ttl = _positive_int("DEFAULT_OFFER_TTL_HOURS", 6)
        if ttl not in (1, 3, 6, 12, 24, 48, 72):
            raise ConfigurationError("DEFAULT_OFFER_TTL_HOURS must be one of 1, 3, 6, 12, 24, 48, 72")

        return cls(
            bot_token=token,
            owner_id=owner_id,
            admin_ids=frozenset(admin_ids),
            sub_channel=os.getenv("SUB_CHANNEL", "").strip().lstrip("@"),
            db_path=Path(os.getenv("DB_PATH", "./data/offers.sqlite3")),
            default_offer_ttl_hours=ttl,
            normal_daily_offers=_positive_int("NORMAL_DAILY_OFFERS", 20),
            vip_daily_offers=_positive_int("VIP_DAILY_OFFERS", 200),
        )

    def is_admin(self, user_id: int) -> bool:
        return user_id == self.owner_id or user_id in self.admin_ids

    def daily_limit(self, plan: str) -> int:
        return self.vip_daily_offers if plan == "vip" else self.normal_daily_offers
