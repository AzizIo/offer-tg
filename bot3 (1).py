#!/usr/bin/env python3
"""Backward-compatible entry point for Offer TG V2.

Configuration is loaded from environment variables or a local .env file.
The bot token and owner credentials must never be stored in this file.
"""

from offerbot.app import main


if __name__ == "__main__":
    main()
