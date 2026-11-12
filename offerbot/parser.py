from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


LINK_RE = re.compile(
    r"https?://(?:t\.me|telegram\.me)/nft/[A-Za-z0-9_-]+",
    flags=re.IGNORECASE,
)
PRICE_RE = re.compile(r"^[0-9]{1,9}$")
COMMAND_RE = re.compile(r"^!\s*(?:прода[её]шь\??|offer)\s*", flags=re.IGNORECASE)
LANGUAGES = {"ru", "en", "zh", "ar"}


@dataclass(frozen=True, slots=True)
class ParsedOffer:
    gift_name: str
    gift_link: str
    price_stars: int
    language: str = "ru"


def _slug_to_name(slug: str) -> str:
    match = re.fullmatch(r"(.+?)-(\d+)", slug)
    if match:
        base, number = match.groups()
        base = re.sub(r"([a-z])([A-Z])", r"\1 \2", base)
        return f"{base.replace('-', ' ')} #{number}"
    return slug.replace("-", " ")


def parse_offer_text(text: str) -> ParsedOffer | None:
    """Parse: optional command/name, NFT URL, integer Stars price, optional language."""
    value = text.strip()
    value = COMMAND_RE.sub("", value, count=1).strip()
    match = LINK_RE.search(value)
    if not match:
        return None

    gift_link = match.group(0).rstrip(".,!?)]}>")
    parsed_url = urlparse(gift_link)
    if parsed_url.scheme not in {"http", "https"}:
        return None
    if (parsed_url.hostname or "").lower() not in {"t.me", "telegram.me"}:
        return None

    path_parts = parsed_url.path.strip("/").split("/")
    if len(path_parts) != 2 or path_parts[0].lower() != "nft" or not path_parts[1]:
        return None

    tail = value[match.end():].strip().lstrip(".,:;—–- ").strip()
    tokens = tail.split()
    if not tokens or not PRICE_RE.fullmatch(tokens[0]):
        return None

    price = int(tokens[0])
    if price <= 0:
        return None

    language = tokens[1].lower() if len(tokens) > 1 and tokens[1].lower() in LANGUAGES else "ru"
    prefix = COMMAND_RE.sub("", value[:match.start()].strip(), count=1).strip()
    gift_name = prefix.strip(" -–—:#") if prefix else _slug_to_name(path_parts[1])
    if not gift_name or len(gift_name) > 64:
        return None

    return ParsedOffer(
        gift_name=gift_name,
        gift_link=gift_link,
        price_stars=price,
        language=language,
    )
