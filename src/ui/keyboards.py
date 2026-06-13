"""All inline keyboards live here so menus stay consistent.

Bot API 9.4 added two relevant fields to ``InlineKeyboardButton``:

* ``icon_custom_emoji_id`` \u2014 a premium custom emoji rendered to the left of
  the label by Telegram itself (as opposed to a plain unicode glyph baked
  into the text).
* ``style`` \u2014 ``"primary"`` (blue), ``"success"`` (green) or ``"danger"``
  (red). Omitted = client default.

The :func:`btn` helper applies both based on a logical emoji name and the
button's semantic role so the colour scheme stays symmetric across the bot:

* navigation / informational buttons \u2192 ``primary`` (blue)
* positive commits (Buy, Confirm, Submit, Generate, Transfer, Enabled-toggle)
  \u2192 ``success`` (green)
* destructive / cancel actions (Cancel, Revoke, Out of stock,
  Disabled-toggle) \u2192 ``danger`` (red)

Both features can be turned off via the ``PREMIUM_BUTTON_ICONS`` and
``BUTTON_STYLES_ENABLED`` env vars (see :mod:`src.config`).
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..config import get_settings
from .emoji import emoji_id, fb

# Callback data tokens. Keep short \u2014 Telegram caps callback_data at 64 bytes.
CB_MAIN = "main"
CB_SHOP = "shop"
CB_DEPOSIT = "deposit"
CB_PROFILE = "profile"
CB_SUPPORT = "support"
CB_REFER = "refer"

CB_REFRESH_SHOP = "shop:refresh"
CB_PRODUCT = "shop:p"           # shop:p:<id>
CB_BUY = "shop:buy"             # shop:buy:<product_id>
CB_BUY_CONFIRM = "shop:bc"      # shop:bc:<product_id>

CB_DEPOSIT_AMOUNT = "dep:amt"   # dep:amt:<amount_cents>
CB_DEPOSIT_CUSTOM = "dep:cust"
CB_DEPOSIT_METHOD = "dep:m"     # dep:m:<binance|upi>:<amount_cents>
CB_DEPOSIT_SUBMIT = "dep:sub"   # dep:sub:<binance|upi>:<amount_cents>
CB_DEPOSIT_TRANSFER_REF = "dep:txfer"

CB_PROFILE_STATS = "prof:stats"
CB_PROFILE_NOTIFS = "prof:notifs"
CB_PROFILE_NOTIFS_TOGGLE = "prof:notifs:t"
CB_PROFILE_ORDERS = "prof:orders"        # prof:orders:<page>
CB_PROFILE_ORDER = "prof:order"          # prof:order:<id>
CB_PROFILE_WITHDRAW = "prof:wd"
CB_PROFILE_WITHDRAW_METHOD = "prof:wd:m"  # prof:wd:m:<binance|upi>
CB_PROFILE_API = "prof:api"
CB_PROFILE_API_NEW = "prof:api:new"
CB_PROFILE_API_REVOKE = "prof:api:rev"   # prof:api:rev:<id>

CB_REFER_COPY = "ref:copy"
CB_REFER_TRANSFER = "ref:txfer"

CB_NOOP = "noop"


# Telegram only accepts these three string values for the ``style`` field.
ButtonStyle = Literal["primary", "success", "danger"]


def _row(*buttons: InlineKeyboardButton) -> list[InlineKeyboardButton]:
    return list(buttons)


def btn(
    label: str,
    *,
    icon: str | None = None,
    style: ButtonStyle | None = "primary",
    callback_data: str | None = None,
    url: str | None = None,
    **extra: object,
) -> InlineKeyboardButton:
    """Build an ``InlineKeyboardButton`` with premium-emoji icon + colour.

    ``icon`` is a logical emoji name (key in ``assets/premium_emojis.json``).
    When premium icons are enabled and the registry has an ID for that name,
    the icon is rendered via the ``icon_custom_emoji_id`` field. Otherwise
    the unicode fallback is prepended to the label so older clients and
    non-Premium owners still get a glyph.

    ``style`` defaults to ``"primary"`` so menu/navigation buttons share a
    consistent blue palette. Use ``"success"`` for positive commits and
    ``"danger"`` for destructive/cancel actions. Pass ``style=None`` to opt
    out and use the client's default colour.
    """
    settings = get_settings()
    text = label
    icon_id: str | None = None
    if icon:
        eid = emoji_id(icon) if settings.premium_button_icons else None
        if eid:
            icon_id = eid
        else:
            glyph = fb(icon)
            if glyph:
                text = f"{glyph} {label}" if label else glyph

    fields: dict[str, object] = {"text": text}
    if icon_id is not None:
        fields["icon_custom_emoji_id"] = icon_id
    if style is not None and settings.button_styles_enabled:
        fields["style"] = style
    if callback_data is not None:
        fields["callback_data"] = callback_data
    if url is not None:
        fields["url"] = url
    fields.update(extra)
    return InlineKeyboardButton(**fields)  # type: ignore[arg-type]


def back_button(target: str = CB_MAIN, label: str | None = None) -> InlineKeyboardButton:
    return btn(label or "Back", icon="back", style="primary", callback_data=target)


def home_button() -> InlineKeyboardButton:
    return btn("Main Menu", icon="home", style="primary", callback_data=CB_MAIN)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(btn("Shop", icon="shop", callback_data=CB_SHOP)),
            _row(
                btn("Deposit", icon="wallet", callback_data=CB_DEPOSIT),
                btn("My Profile", icon="user", callback_data=CB_PROFILE),
            ),
            _row(btn("Support", icon="support", callback_data=CB_SUPPORT)),
            _row(btn("Refer & Earn", icon="refer", callback_data=CB_REFER)),
        ]
    )


def shop_list_kb(
    products: Iterable[tuple[int, str, str, str | None, str, int]],
) -> InlineKeyboardMarkup:
    """Build the shop product list.

    ``products`` yields ``(id, display_name, emoji, emoji_id, duration, stock)``
    tuples \u2014 ``emoji_id`` is the per-product premium custom emoji id from
    the ``products.emoji_id`` column (may be ``None``).
    """
    settings = get_settings()
    rows: list[list[InlineKeyboardButton]] = []
    for pid, name, emoji, eid, duration, stock in products:
        label = f"{name} {duration} ({stock})"
        fields: dict[str, object] = {
            "text": label,
            "callback_data": f"{CB_PRODUCT}:{pid}",
        }
        if settings.premium_button_icons and eid:
            fields["icon_custom_emoji_id"] = str(eid)
        else:
            fields["text"] = f"{emoji} {label}" if emoji else label
        if settings.button_styles_enabled:
            fields["style"] = "primary"
        rows.append(_row(InlineKeyboardButton(**fields)))  # type: ignore[arg-type]
    rows.append(_row(btn("Refresh", icon="refresh", callback_data=CB_REFRESH_SHOP)))
    rows.append(_row(back_button(CB_MAIN)))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_kb(product_id: int, can_buy: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_buy:
        rows.append(_row(
            btn("Buy now", icon="cart", style="success",
                callback_data=f"{CB_BUY}:{product_id}")
        ))
    else:
        rows.append(_row(
            btn("Out of stock", icon="cross", style="danger", callback_data=CB_NOOP)
        ))
    rows.append(_row(back_button(CB_SHOP), home_button()))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buy_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(
                btn("Confirm", icon="check", style="success",
                    callback_data=f"{CB_BUY_CONFIRM}:{product_id}"),
                btn("Cancel", icon="cross", style="danger",
                    callback_data=f"{CB_PRODUCT}:{product_id}"),
            ),
        ]
    )


def deposit_kb(*, has_referral_balance: bool) -> InlineKeyboardMarkup:
    amounts = [5, 10, 25, 50, 100]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for amt in amounts:
        row.append(btn(
            f"{amt} USDT", style="primary",
            callback_data=f"{CB_DEPOSIT_AMOUNT}:{int(amt*100)}",
        ))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(_row(btn("Custom amount", icon="coin", callback_data=CB_DEPOSIT_CUSTOM)))
    if has_referral_balance:
        rows.append(_row(btn(
            "Transfer Referral \u2192 Wallet",
            icon="transfer", style="success",
            callback_data=CB_DEPOSIT_TRANSFER_REF,
        )))
    rows.append(_row(back_button(CB_MAIN)))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def deposit_method_kb(amount_cents: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(
                btn("Binance UID", icon="binance",
                    callback_data=f"{CB_DEPOSIT_METHOD}:binance:{amount_cents}"),
                btn("UPI", icon="upi",
                    callback_data=f"{CB_DEPOSIT_METHOD}:upi:{amount_cents}"),
            ),
            _row(back_button(CB_DEPOSIT)),
        ]
    )


def deposit_submit_kb(method: str, amount_cents: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(btn(
                "I've paid \u2014 submit proof",
                icon="check", style="success",
                callback_data=f"{CB_DEPOSIT_SUBMIT}:{method}:{amount_cents}",
            )),
            _row(back_button(CB_DEPOSIT)),
        ]
    )


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(
                btn("My Stats", icon="stats", callback_data=CB_PROFILE_STATS),
                btn("Notifications", icon="bell", callback_data=CB_PROFILE_NOTIFS),
            ),
            _row(
                btn("My Orders", icon="orders", callback_data=f"{CB_PROFILE_ORDERS}:1"),
                btn("Withdraw", icon="withdraw", callback_data=CB_PROFILE_WITHDRAW),
            ),
            _row(btn("Developer API", icon="api", callback_data=CB_PROFILE_API)),
            _row(back_button(CB_MAIN)),
        ]
    )


def notifs_kb(enabled: bool) -> InlineKeyboardMarkup:
    if enabled:
        toggle = btn(
            "Enabled \u2014 tap to disable",
            icon="check", style="success",
            callback_data=CB_PROFILE_NOTIFS_TOGGLE,
        )
    else:
        toggle = btn(
            "Disabled \u2014 tap to enable",
            icon="cross", style="danger",
            callback_data=CB_PROFILE_NOTIFS_TOGGLE,
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(toggle),
            _row(back_button(CB_PROFILE)),
        ]
    )


def orders_kb(orders: list[tuple[int, str]], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for oid, label in orders:
        rows.append(_row(btn(
            label, style="primary",
            callback_data=f"{CB_PROFILE_ORDER}:{oid}",
        )))
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(btn("\u25c0 Prev", style="primary",
                       callback_data=f"{CB_PROFILE_ORDERS}:{page-1}"))
    if has_next:
        nav.append(btn("Next \u25b6", style="primary",
                       callback_data=f"{CB_PROFILE_ORDERS}:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append(_row(back_button(CB_PROFILE)))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_detail_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(back_button(f"{CB_PROFILE_ORDERS}:1", label="My Orders"), home_button()),
        ]
    )


def withdraw_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(
                btn("Binance UID", icon="binance",
                    callback_data=f"{CB_PROFILE_WITHDRAW_METHOD}:binance"),
                btn("UPI", icon="upi",
                    callback_data=f"{CB_PROFILE_WITHDRAW_METHOD}:upi"),
            ),
            _row(back_button(CB_PROFILE)),
        ]
    )


def withdraw_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[_row(btn(
            "Cancel", icon="cross", style="danger", callback_data=CB_PROFILE,
        ))]
    )


def api_kb(has_token: bool, token_id: int | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_token and token_id is not None:
        rows.append(_row(btn(
            "Revoke token", icon="cross", style="danger",
            callback_data=f"{CB_PROFILE_API_REVOKE}:{token_id}",
        )))
    rows.append(_row(btn(
        "Generate new token", icon="rocket", style="success",
        callback_data=CB_PROFILE_API_NEW,
    )))
    rows.append(_row(back_button(CB_PROFILE)))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_kb(support_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(btn("Contact Support", icon="support",
                     url=f"https://t.me/{support_username}")),
            _row(back_button(CB_MAIN)),
        ]
    )


def refer_kb(referral_link: str, has_balance: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    # ``copy_text`` was added to Bot API 7.10 \u2014 when the user taps it
    # Telegram copies the link to their clipboard with no extra dialog.
    try:
        from aiogram.types import CopyTextButton
        copy_btn = btn(
            "Copy Referral Link", icon="clipboard",
            copy_text=CopyTextButton(text=referral_link),
        )
    except Exception:
        # Older aiogram or older Telegram client \u2014 fall back to a callback
        # that shows the link in an alert so it can be copied manually.
        copy_btn = btn(
            "Copy Referral Link", icon="clipboard",
            callback_data=CB_REFER_COPY,
        )
    rows.append(_row(copy_btn))
    rows.append(_row(btn(
        "Share with a friend", icon="link",
        url=f"https://t.me/share/url?url={referral_link}",
    )))
    if has_balance:
        rows.append(_row(btn(
            "Transfer to Wallet", icon="transfer", style="success",
            callback_data=CB_REFER_TRANSFER,
        )))
    rows.append(_row(back_button(CB_MAIN)))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[_row(btn(
            "Cancel", icon="cross", style="danger", callback_data=CB_MAIN,
        ))]
    )
