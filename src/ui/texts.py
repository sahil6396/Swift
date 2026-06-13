"""Message body builders. All in HTML mode so we can mix premium emojis."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from html import escape

from ..config import get_settings
from .emoji import pe, pe_custom


def _h(s: str) -> str:
    return escape(s, quote=False)


def main_menu(user_first_name: str) -> str:
    s = get_settings()
    name = _h(user_first_name or "friend")
    return (
        f"{pe('sparkle')} <b>Welcome to {_h(s.shop_name)}!</b>\n\n"
        f"Hey, <b>{name}</b> {pe('wave')}\n\n"
        "We offer premium digital products at the best prices. Fast, secure, "
        "and fully automated delivery.\n\n"
        f"<blockquote>"
        f"{pe('shop')} <b>Shop</b> — Browse &amp; buy products\n"
        f"{pe('wallet')} <b>Deposit</b> — Add funds to your wallet\n"
        f"{pe('user')} <b>My Profile</b> — Balance, orders &amp; settings\n"
        f"{pe('support')} <b>Support</b> — Get help\n"
        f"{pe('refer')} <b>Refer &amp; Earn</b> — Invite friends &amp; earn rewards"
        f"</blockquote>\n\n"
        f"Choose an option below to continue! {pe('point_down')}"
    )


def shop_header(total: int) -> str:
    return (
        f"{pe('cart')} <b>Choose Your Product</b>\n\n"
        f"{total} item(s) available. Tap any product to see details and buy.\n"
        "<i>Numbers in parentheses show the live stock count.</i>"
    )


def shop_empty() -> str:
    return (
        f"{pe('cart')} <b>Shop</b>\n\n"
        f"{pe('warning')} No products available right now. Please check back soon."
    )


def product_detail(
    *, name: str, emoji: str, emoji_id: str | None, duration: str, price: Decimal,
    description: str, stock: int,
) -> str:
    desc = _h(description.strip()) if description.strip() else "<i>No description.</i>"
    stock_line = (
        f"{pe('check')} <b>In stock:</b> {stock}" if stock > 0
        else f"{pe('cross')} <b>Out of stock</b>"
    )
    rendered_emoji = pe_custom(emoji_id, emoji)
    return (
        f"{rendered_emoji} <b>{_h(name)}</b> · <code>{_h(duration)}</code>\n\n"
        f"{pe('coin')} <b>Price:</b> {price:.2f} USDT\n"
        f"{stock_line}\n\n"
        f"{desc}"
    )


def buy_confirm(*, name: str, price: Decimal, balance: Decimal) -> str:
    return (
        f"{pe('cart')} <b>Confirm purchase</b>\n\n"
        f"Product: <b>{_h(name)}</b>\n"
        f"Price: <b>{price:.2f} USDT</b>\n"
        f"Your balance: <b>{balance:.2f} USDT</b>\n"
        f"After purchase: <b>{(balance - price):.2f} USDT</b>\n\n"
        "Press <b>Confirm</b> to complete."
    )


def buy_insufficient(*, price: Decimal, balance: Decimal) -> str:
    short = price - balance
    return (
        f"{pe('warning')} <b>Insufficient balance</b>\n\n"
        f"Price: <b>{price:.2f} USDT</b>\n"
        f"Your balance: <b>{balance:.2f} USDT</b>\n"
        f"Short by: <b>{short:.2f} USDT</b>\n\n"
        "Tap <b>Deposit</b> to top up your wallet."
    )


def buy_success(*, name: str, payload: str, order_id: int) -> str:
    return (
        f"{pe('check')} <b>Purchase successful!</b>\n\n"
        f"Product: <b>{_h(name)}</b>\n"
        f"Order #: <code>{order_id}</code>\n\n"
        f"{pe('lock')} <b>Your credentials:</b>\n"
        f"<pre>{_h(payload)}</pre>\n\n"
        "Save this info — you can also find it later under <b>My Profile → My Orders</b>."
    )


def deposit(
    *,
    balance: Decimal,
    referral_available: Decimal,
    referral_total_earned: Decimal,
    binance_uid: str,
    upi_id: str,
) -> str:
    refs = (
        f"{pe('refer')} <b>Referral (Available):</b> {referral_available:.2f} USDT\n"
        f"{pe('refer')} <b>Referral (Total earned):</b> {referral_total_earned:.2f} USDT\n"
    )
    methods = []
    if binance_uid:
        methods.append(f"{pe('binance')} Binance Pay (UID)")
    if upi_id:
        methods.append(f"{pe('upi')} UPI")
    methods_line = (
        "Accepted methods: " + " · ".join(methods)
        if methods else f"{pe('warning')} <i>No deposit methods configured yet.</i>"
    )
    return (
        f"{pe('wallet')} <b>Deposit</b>\n\n"
        f"{pe('coin')} <b>Wallet balance:</b> {balance:.2f} USDT\n"
        f"{refs}\n"
        "Choose a deposit amount or transfer your referral earnings:\n\n"
        f"{methods_line}"
    )


def deposit_method_choose(amount: Decimal) -> str:
    return (
        f"{pe('wallet')} <b>Deposit · {amount:.2f} USDT</b>\n\n"
        "Choose a payment method:"
    )


def deposit_instructions_binance(*, amount: Decimal, uid: str) -> str:
    if not uid:
        return (
            f"{pe('warning')} <b>Binance UID not configured</b>\n\n"
            "Ask the admin to set <code>BINANCE_UID</code> in the bot config."
        )
    return (
        f"{pe('binance')} <b>Pay {amount:.2f} USDT via Binance Pay</b>\n\n"
        f"Send to Binance UID:\n<code>{_h(uid)}</code>\n\n"
        f"Amount: <b>{amount:.2f} USDT</b>\n\n"
        "After paying, tap the button below and forward the screenshot or paste "
        "the transaction ID. An admin will verify and credit your wallet within "
        "a few minutes."
    )


def deposit_instructions_upi(*, amount: Decimal, upi_id: str, upi_name: str) -> str:
    if not upi_id:
        return (
            f"{pe('warning')} <b>UPI not configured</b>\n\n"
            "Ask the admin to set <code>UPI_ID</code> in the bot config."
        )
    name_line = f"\nName: <b>{_h(upi_name)}</b>" if upi_name else ""
    return (
        f"{pe('upi')} <b>Pay {amount:.2f} USDT via UPI</b>\n\n"
        f"UPI ID:\n<code>{_h(upi_id)}</code>{name_line}\n\n"
        f"Amount: <b>{amount:.2f} USDT</b> (in INR equivalent)\n\n"
        "After paying, tap the button below and send the UTR / transaction "
        "reference. An admin will verify and credit your wallet."
    )


def deposit_ask_proof(method: str, amount: Decimal) -> str:
    return (
        f"{pe('wallet')} <b>Submit payment proof</b>\n\n"
        f"Method: <b>{method.upper()}</b>\n"
        f"Amount: <b>{amount:.2f} USDT</b>\n\n"
        "Send your <b>transaction ID / UTR / screenshot</b> as the next message. "
        "Send <code>cancel</code> to abort."
    )


def deposit_submitted(deposit_id: int) -> str:
    return (
        f"{pe('check')} <b>Deposit submitted</b>\n\n"
        f"Ticket #: <code>{deposit_id}</code>\n\n"
        "An admin will verify your payment shortly. You'll get a notification "
        "when your wallet is credited."
    )


def deposit_custom_prompt() -> str:
    return (
        f"{pe('coin')} <b>Custom deposit amount</b>\n\n"
        "Send the amount in <b>USDT</b> (e.g. <code>15</code> or <code>27.50</code>). "
        "Minimum 1 USDT. Send <code>cancel</code> to abort."
    )


def profile(
    *, user_id: int, balance: Decimal, joined_at: datetime,
) -> str:
    return (
        f"{pe('user')} <b>User Profile</b>\n\n"
        f"{pe('id')} <b>ID:</b> <code>{user_id}</code>\n"
        f"{pe('coin')} <b>Balance:</b> {balance:.2f} USDT\n"
        f"{pe('calendar')} <b>Joined:</b> {joined_at.strftime('%Y-%m-%d')}"
    )


def profile_stats(
    *, total_orders: int, total_spent: Decimal, total_deposited: Decimal,
    referrals: int, referral_earned: Decimal,
) -> str:
    return (
        f"{pe('stats')} <b>My Stats</b>\n\n"
        f"Total orders: <b>{total_orders}</b>\n"
        f"Total spent: <b>{total_spent:.2f} USDT</b>\n"
        f"Total deposited: <b>{total_deposited:.2f} USDT</b>\n"
        f"Referrals: <b>{referrals}</b>\n"
        f"Referral earnings: <b>{referral_earned:.2f} USDT</b>"
    )


def profile_notifs(enabled: bool) -> str:
    state = "<b>ON</b>" if enabled else "<b>OFF</b>"
    return (
        f"{pe('bell')} <b>Notifications</b>\n\n"
        f"Status: {state}\n\n"
        "When ON, you'll receive order updates, deposit confirmations, "
        "withdrawal status, and admin announcements."
    )


def profile_orders_header(total: int, page: int, page_size: int) -> str:
    if total == 0:
        return (
            f"{pe('orders')} <b>My Orders</b>\n\n"
            "<i>No orders yet. Browse the shop to make your first purchase.</i>"
        )
    pages = max(1, (total + page_size - 1) // page_size)
    return (
        f"{pe('orders')} <b>My Orders</b>\n\n"
        f"Total: <b>{total}</b> · Page {page}/{pages}"
    )


def order_detail(*, order_id: int, name: str, price: Decimal, payload: str, created_at: datetime) -> str:
    return (
        f"{pe('orders')} <b>Order #{order_id}</b>\n\n"
        f"Product: <b>{_h(name)}</b>\n"
        f"Price: <b>{price:.2f} USDT</b>\n"
        f"Date: {created_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"{pe('lock')} <b>Credentials:</b>\n"
        f"<pre>{_h(payload)}</pre>"
    )


def withdraw_intro(*, balance: Decimal, min_amt: Decimal, max_amt: Decimal) -> str:
    return (
        f"{pe('withdraw')} <b>Withdraw</b>\n\n"
        f"Balance: <b>{balance:.2f} USDT</b>\n"
        f"Limits: {min_amt:.2f} – {max_amt:.2f} USDT\n\n"
        "Choose a payout method:"
    )


def withdraw_ask_amount(method: str, balance: Decimal) -> str:
    return (
        f"{pe('withdraw')} <b>Withdraw via {method.upper()}</b>\n\n"
        f"Balance: <b>{balance:.2f} USDT</b>\n\n"
        "Send the amount in <b>USDT</b> (e.g. <code>10</code>). "
        "Send <code>cancel</code> to abort."
    )


def withdraw_ask_address(method: str, amount: Decimal) -> str:
    addr_label = "Binance UID" if method == "binance" else "UPI ID"
    return (
        f"{pe('withdraw')} <b>Withdraw {amount:.2f} USDT via {method.upper()}</b>\n\n"
        f"Send your <b>{addr_label}</b> as the next message.\n"
        "Send <code>cancel</code> to abort."
    )


def withdraw_submitted(wid: int) -> str:
    return (
        f"{pe('check')} <b>Withdrawal request submitted</b>\n\n"
        f"Ticket #: <code>{wid}</code>\n\n"
        "An admin will process it within 24 hours."
    )


def api_screen(token: str | None) -> str:
    if not token:
        return (
            f"{pe('api')} <b>Developer API</b>\n\n"
            "<i>You don't have an API token yet.</i>\n\n"
            "Generate one to programmatically check stock and place orders. "
            "Endpoint docs: <code>/api/docs</code> on the admin dashboard."
        )
    return (
        f"{pe('api')} <b>Developer API</b>\n\n"
        f"Token: <code>{_h(token)}</code>\n\n"
        f"{pe('warning')} Keep this secret. Anyone with it can act as you."
    )


def api_token_created(token: str) -> str:
    return (
        f"{pe('check')} <b>New API token</b>\n\n"
        f"<code>{_h(token)}</code>\n\n"
        f"{pe('warning')} Copy it now — for security we'll only show it on this screen."
    )


def support_screen() -> str:
    s = get_settings()
    return (
        f"{pe('support')} <b>Need Help?</b>\n\n"
        "Contact our support team directly:\n"
        f"<b>@{_h(s.support_username)}</b>"
    )


def refer_screen(
    *, ref_24h: int, ref_7d: int, ref_total: int,
    earned_total: Decimal, available: Decimal, transferred: Decimal,
    referral_link: str, commission_pct: Decimal, first_purchase_bonus: Decimal,
) -> str:
    return (
        f"{pe('refer')} <b>Refer &amp; Earn</b>\n\n"
        f"{pe('people')} <b>Referred (24h):</b> {ref_24h}\n"
        f"{pe('people')} <b>Referred (7d):</b> {ref_7d}\n"
        f"{pe('people')} <b>Referred (Total):</b> {ref_total}\n\n"
        f"{pe('coin')} <b>Total Earned:</b> {earned_total:.2f} USDT\n"
        f"{pe('coin')} <b>Available:</b> {available:.2f} USDT\n"
        f"{pe('coin')} <b>Transferred:</b> {transferred:.2f} USDT\n\n"
        f"<blockquote>Earn <b>{commission_pct}%</b> of every purchase &amp; deposit by your referred users.\n"
        f"+<b>{first_purchase_bonus:.2f} USDT</b> bonus on their first purchase.\n"
        "Transfer earnings to your wallet anytime.</blockquote>\n\n"
        f"<b>Your referral link:</b>\n<code>{_h(referral_link)}</code>"
    )


def transfer_done(amount: Decimal) -> str:
    return (
        f"{pe('check')} <b>Transferred</b>\n\n"
        f"Moved <b>{amount:.2f} USDT</b> from referral earnings to your wallet."
    )


def transfer_nothing() -> str:
    return (
        f"{pe('info')} <b>Nothing to transfer</b>\n\n"
        "You have no available referral earnings right now."
    )


def banned() -> str:
    return f"{pe('cross')} <b>Your account is banned.</b> Contact support."


def help_text() -> str:
    return (
        f"{pe('info')} <b>How to use this bot</b>\n\n"
        f"{pe('shop')} <b>Shop</b> — pick a product, see the price and stock count, then tap "
        f"<b>Buy now</b>. Make sure your wallet balance covers the price.\n\n"
        f"{pe('wallet')} <b>Deposit</b> — choose an amount, pick Binance UID or UPI, send the "
        f"payment, then submit your transaction ID or screenshot. An admin approves "
        f"and your wallet is credited.\n\n"
        f"{pe('user')} <b>My Profile</b> — see your wallet balance, order history, "
        f"toggle notifications, withdraw funds, generate an API token.\n\n"
        f"{pe('refer')} <b>Refer &amp; Earn</b> — share your referral link to earn a "
        f"commission on every purchase &amp; deposit your friends make, plus a bonus on "
        f"their first purchase.\n\n"
        f"{pe('support')} <b>Support</b> — chat with our team if anything goes wrong.\n\n"
        "<blockquote>Tip: every button updates the same message instead of spamming "
        "new ones. Use the <b>Back</b> and <b>Main Menu</b> buttons to navigate.</blockquote>"
    )
