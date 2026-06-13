"""Settings loaded from environment / .env file."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str = Field(..., alias="BOT_TOKEN")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")
    # If empty, src.main fills this in from getMe() at startup so referral links
    # always use the correct username.
    bot_username: str = Field("", alias="BOT_USERNAME")

    shop_name: str = Field("Baba Swift Shop", alias="SHOP_NAME")
    support_username: str = Field("babaswiftbot", alias="SUPPORT_USERNAME")

    binance_uid: str = Field("", alias="BINANCE_UID")
    upi_id: str = Field("", alias="UPI_ID")
    upi_name: str = Field("", alias="UPI_NAME")

    database_url: str = Field(
        "sqlite+aiosqlite:///./data/bot.db", alias="DATABASE_URL"
    )

    dashboard_host: str = Field("127.0.0.1", alias="DASHBOARD_HOST")
    dashboard_port: int = Field(8088, alias="DASHBOARD_PORT")
    dashboard_password: str = Field("change_me", alias="DASHBOARD_PASSWORD")
    dashboard_session_secret: str = Field("change_me_session", alias="DASHBOARD_SESSION_SECRET")

    referral_commission_pct: Decimal = Field(Decimal("2.0"), alias="REFERRAL_COMMISSION_PCT")
    referral_first_purchase_bonus_usdt: Decimal = Field(
        Decimal("0.50"), alias="REFERRAL_FIRST_PURCHASE_BONUS_USDT"
    )

    withdraw_min: Decimal = Field(Decimal("5"), alias="WITHDRAW_MIN")
    withdraw_max: Decimal = Field(Decimal("1000"), alias="WITHDRAW_MAX")

    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Premium custom emojis on inline keyboard buttons (Bot API 9.4+).
    # Requires the bot owner to hold a Telegram Premium subscription. When
    # disabled the unicode fallback glyphs from premium_emojis.json are
    # rendered inside button labels instead.
    premium_button_icons: bool = Field(True, alias="PREMIUM_BUTTON_ICONS")
    # Coloured inline keyboard buttons (Bot API 9.4+ ``style`` field with
    # ``primary`` / ``success`` / ``danger``). Disable to fall back to the
    # client's default button colour everywhere.
    button_styles_enabled: bool = Field(True, alias="BUTTON_STYLES_ENABLED")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v: object) -> list[int]:
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [int(x) for x in v]
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return [int(v)]  # type: ignore[arg-type]

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
