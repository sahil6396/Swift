"""SQLAlchemy models. Schema mirrors the plan in baba_swift_bot_plan.md."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

NUMERIC = Numeric(18, 6)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram user_id
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    balance_usdt: Mapped[Decimal] = mapped_column(NUMERIC, default=Decimal("0"))
    referral_code: Mapped[str] = mapped_column(String(16), unique=True)
    referred_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_menu_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(128))
    emoji: Mapped[str] = mapped_column(String(16), default="📦")  # standard emoji fallback
    emoji_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # premium custom_emoji_id
    duration_label: Mapped[str] = mapped_column(String(16), default="12m")
    price_usdt: Mapped[Decimal] = mapped_column(NUMERIC, default=Decimal("0"))
    description: Mapped[str] = mapped_column(Text, default="")
    delivery_type: Mapped[str] = mapped_column(String(16), default="stock_pool")
    api_handler: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"))
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="available")  # available|sold
    sold_to: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"))
    stock_item_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stock_items.id"), nullable=True
    )
    price_usdt: Mapped[Decimal] = mapped_column(NUMERIC)
    payload_snapshot: Mapped[str] = mapped_column(Text, default="")  # delivered content snapshot
    status: Mapped[str] = mapped_column(String(16), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Deposit(Base):
    __tablename__ = "deposits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    method: Mapped[str] = mapped_column(String(16))  # 'binance' | 'upi'
    amount_usdt: Mapped[Decimal] = mapped_column(NUMERIC)
    txn_reference: Mapped[str] = mapped_column(String(255), default="")
    proof_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected
    admin_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    amount_usdt: Mapped[Decimal] = mapped_column(NUMERIC)
    method: Mapped[str] = mapped_column(String(16))  # 'binance' | 'upi'
    address: Mapped[str] = mapped_column(String(255))  # binance UID or UPI id
    status: Mapped[str] = mapped_column(String(16), default="pending")
    admin_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class ReferralEarning(Base):
    __tablename__ = "referral_earnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    source_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    source_event: Mapped[str] = mapped_column(String(32))  # 'deposit'|'purchase'|'first_purchase_bonus'
    source_ref_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount_usdt: Mapped[Decimal] = mapped_column(NUMERIC)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(32))
    amount_usdt: Mapped[Decimal] = mapped_column(NUMERIC)
    ref_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(64), default="default")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    """Generic key/value runtime configuration (broadcasts, banners, etc.)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
