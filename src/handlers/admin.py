"""In-bot admin commands. Admin IDs come from settings.admin_ids."""
from __future__ import annotations

import contextlib
import logging
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Document, Message
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db.models import Deposit, Order, Product, StockItem, Transaction, User, Withdrawal
from ..repositories import deposits as deposits_repo
from ..repositories import products as products_repo
from ..repositories import withdrawals as wd_repo
from ..repositories.users import get_user
from ..services import wallet
from ..services.referral import reward_on_deposit
from ..ui.emoji import pe, reload_map
from .states import AdminStates

router = Router(name="admin")
log = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_ids


@router.message(Command("admin"))
async def admin_help(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "<b>Admin commands</b>\n\n"
        "<b>Stock &amp; products</b>\n"
        "<code>/products</code> — list products with stock\n"
        "<code>/addproduct slug|Name|emoji|duration|price</code>\n"
        "<code>/setprice slug 24.99</code>\n"
        "<code>/setactive slug on|off</code>\n"
        "<code>/setdesc slug Description text...</code>\n"
        "<code>/setemoji slug ID</code> — bind a premium custom_emoji_id (or <code>clear</code>)\n"
        "<code>/addstock slug</code> — then send a .txt with one credential per line\n"
        "<code>/stock slug</code> — show available stock count\n"
        "<code>/clearstock slug confirm</code> — delete all unsold stock\n"
        "<code>/delproduct slug confirm</code> — hard-delete a product (must have no orders)\n\n"
        "<b>Deposits</b>\n"
        "<code>/deposits</code> — pending deposits\n"
        "<code>/approve_dep ID</code>\n"
        "<code>/reject_dep ID reason</code>\n\n"
        "<b>Withdrawals</b>\n"
        "<code>/withdrawals</code> — pending\n"
        "<code>/approve_wd ID</code>\n"
        "<code>/reject_wd ID reason</code>\n\n"
        "<b>Users</b>\n"
        "<code>/whois USER_ID</code>\n"
        "<code>/credit USER_ID 10.00 reason</code>\n"
        "<code>/debit USER_ID 5.00 reason</code>\n"
        "<code>/ban USER_ID</code> / <code>/unban USER_ID</code>\n\n"
        "<b>Other</b>\n"
        "<code>/broadcast</code> — then send the message to broadcast\n"
        "<code>/getemoji</code> — reply to a message containing premium emojis to capture their IDs\n"
        "<code>/reload_emojis</code> — re-read assets/premium_emojis.json\n"
        "<code>/stats</code> — bot stats",
        parse_mode="HTML",
    )


# ─── Products ─────────────────────────────────────────────────────────────────

@router.message(Command("products"))
async def list_products(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    items = await products_repo.list_active_products_with_stock(session)
    if not items:
        await message.answer("No products yet.")
        return
    lines = []
    for p, stock in items:
        active = pe("check") if p.is_active else pe("disabled")
        lines.append(
            f"{active} <b>{p.slug}</b> · {p.emoji} {p.display_name} {p.duration_label} · "
            f"{p.price_usdt:.2f} USDT · stock {stock}"
        )
    # Also show inactive
    inactive = (await session.scalars(
        select(Product).where(Product.is_active.is_(False))
    )).all()
    for p in inactive:
        lines.append(f"{pe('disabled')} <b>{p.slug}</b> · {p.emoji} {p.display_name} {p.duration_label} · {p.price_usdt:.2f} USDT (inactive)")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("addproduct"))
async def addproduct(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = (command.args or "").strip()
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 5:
        await message.answer("Usage: /addproduct slug|Name|emoji|duration|price")
        return
    slug, name, emoji, duration, price_str = parts[:5]
    try:
        price = Decimal(price_str)
    except InvalidOperation:
        await message.answer("Invalid price.")
        return
    p = await products_repo.upsert_product(
        session,
        slug=slug, display_name=name, emoji=emoji,
        duration_label=duration, price_usdt=price,
    )
    await message.answer(f"Saved: <b>{p.slug}</b> · {p.emoji} {p.display_name} {p.duration_label} · {p.price_usdt:.2f} USDT",
                         parse_mode="HTML")


@router.message(Command("setprice"))
async def setprice(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /setprice slug 24.99")
        return
    slug, price_str = parts
    try:
        price = Decimal(price_str)
    except InvalidOperation:
        await message.answer("Invalid price.")
        return
    p = await session.scalar(select(Product).where(Product.slug == slug))
    if p is None:
        await message.answer("Product not found.")
        return
    p.price_usdt = price
    await session.commit()
    await message.answer(f"Updated price for <b>{slug}</b> → {price:.2f} USDT", parse_mode="HTML")


@router.message(Command("setactive"))
async def setactive(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /setactive slug on|off")
        return
    slug, mode = parts
    p = await session.scalar(select(Product).where(Product.slug == slug))
    if p is None:
        await message.answer("Product not found.")
        return
    p.is_active = mode.lower() == "on"
    await session.commit()
    await message.answer(f"<b>{slug}</b> is now {'ACTIVE' if p.is_active else 'INACTIVE'}", parse_mode="HTML")


@router.message(Command("setdesc"))
async def setdesc(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = (command.args or "")
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /setdesc slug description text")
        return
    slug, desc = parts
    p = await session.scalar(select(Product).where(Product.slug == slug))
    if p is None:
        await message.answer("Product not found.")
        return
    p.description = desc
    await session.commit()
    await message.answer(f"Description updated for <b>{slug}</b>", parse_mode="HTML")


@router.message(Command("setemoji"))
async def setemoji(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """Set or clear the premium custom_emoji_id for a product.

    Usage:
        /setemoji slug 5368324170671202286   — bind a premium emoji
        /setemoji slug clear                  — drop the premium binding
    """
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if len(parts) < 2:
        await message.answer(
            "Usage: <code>/setemoji slug ID</code> or <code>/setemoji slug clear</code>\n\n"
            "Use <code>/getemoji</code> by replying to a message with premium emojis "
            "to capture their IDs.",
            parse_mode="HTML",
        )
        return
    slug, val = parts[0], parts[1]
    p = await session.scalar(select(Product).where(Product.slug == slug))
    if p is None:
        await message.answer("Product not found.")
        return
    if val.lower() == "clear":
        p.emoji_id = None
        await session.commit()
        await message.answer(f"Cleared premium emoji for <b>{slug}</b>.", parse_mode="HTML")
        return
    if not val.isdigit():
        await message.answer(
            "Premium emoji ID must be a number. Use <code>/getemoji</code> to fetch it.",
            parse_mode="HTML",
        )
        return
    p.emoji_id = val
    await session.commit()
    await message.answer(
        f"Premium emoji set for <b>{slug}</b>: "
        f'<tg-emoji emoji-id="{val}">{p.emoji}</tg-emoji>',
        parse_mode="HTML",
    )


@router.message(Command("addstock"))
async def addstock_cmd(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    slug = (command.args or "").strip()
    if not slug:
        await message.answer("Usage: /addstock slug — then send a .txt file with one credential per line.")
        return
    p = await session.scalar(select(Product).where(Product.slug == slug))
    if p is None:
        await message.answer("Product not found.")
        return
    await state.set_state(AdminStates.waiting_stock_upload)
    await state.update_data(product_id=p.id, slug=slug)
    await message.answer(
        f"Send the stock as a <b>.txt file</b> (one credential per line) or as a plain message. "
        f"Adding to <b>{slug}</b>.",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_stock_upload)
async def addstock_upload(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    pid = int(data["product_id"])
    slug = data.get("slug", "?")
    lines: list[str] = []
    if isinstance(message.document, Document):
        # Download the file
        f = await message.bot.get_file(message.document.file_id)
        bio = await message.bot.download_file(f.file_path)
        text = bio.read().decode("utf-8", errors="replace")
        lines = text.splitlines()
    elif message.text:
        lines = message.text.splitlines()
    else:
        await message.answer("Send a .txt file or paste lines.")
        return
    n = await products_repo.add_stock_lines(session, pid, lines)
    await state.clear()
    await message.answer(f"Added <b>{n}</b> stock items to <b>{slug}</b>.", parse_mode="HTML")


@router.message(Command("stock"))
async def stock_count(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    slug = (command.args or "").strip()
    p = await session.scalar(select(Product).where(Product.slug == slug))
    if p is None:
        await message.answer("Product not found.")
        return
    n = await products_repo.count_available_stock(session, p.id)
    await message.answer(f"<b>{slug}</b>: {n} available", parse_mode="HTML")


@router.message(Command("clearstock"))
async def clearstock(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if not parts:
        await message.answer(
            "Usage: <code>/clearstock slug confirm</code>\n"
            "Removes all <b>unsold</b> stock items for the product. "
            "Sold items stay so order history is preserved.",
            parse_mode="HTML",
        )
        return
    slug = parts[0]
    confirm = parts[1].lower() if len(parts) > 1 else ""
    p = await session.scalar(select(Product).where(Product.slug == slug))
    if p is None:
        await message.answer("Product not found.")
        return
    n_avail = await products_repo.count_available_stock(session, p.id)
    if confirm != "confirm":
        await message.answer(
            f"<b>{slug}</b> has {n_avail} unsold stock items. "
            f"Run <code>/clearstock {slug} confirm</code> to delete them.",
            parse_mode="HTML",
        )
        return
    deleted = await products_repo.clear_available_stock(session, p.id)
    await message.answer(f"Removed <b>{deleted}</b> unsold stock items from <b>{slug}</b>.",
                         parse_mode="HTML")


@router.message(Command("delproduct"))
async def delproduct(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split()
    if not parts:
        await message.answer(
            "Usage: <code>/delproduct slug confirm</code>\n"
            "Hard-deletes the product. Refuses if there is any order history "
            "(use <code>/setactive slug off</code> to hide instead).",
            parse_mode="HTML",
        )
        return
    slug = parts[0]
    confirm = parts[1].lower() if len(parts) > 1 else ""
    p = await session.scalar(select(Product).where(Product.slug == slug))
    if p is None:
        await message.answer("Product not found.")
        return
    n_orders = await products_repo.count_orders(session, p.id)
    n_avail = await products_repo.count_available_stock(session, p.id)
    if confirm != "confirm":
        await message.answer(
            f"<b>{slug}</b> · {p.emoji} {p.display_name}\n"
            f"Orders on record: <b>{n_orders}</b>\n"
            f"Unsold stock items: <b>{n_avail}</b>\n\n"
            + (f"{pe('warning')} Cannot delete — has order history. Use "
               f"<code>/setactive {slug} off</code> to hide instead.\n"
               if n_orders > 0
               else f"Run <code>/delproduct {slug} confirm</code> to permanently delete."),
            parse_mode="HTML",
        )
        return
    ok, msg = await products_repo.delete_product(session, p.id)
    await message.answer(msg)


# ─── Deposits ─────────────────────────────────────────────────────────────────

@router.message(Command("deposits"))
async def list_deposits(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    pending = await deposits_repo.get_pending_deposits(session)
    if not pending:
        await message.answer("No pending deposits.")
        return
    lines = []
    for d in pending:
        lines.append(
            f"#{d.id} · user <code>{d.user_id}</code> · {d.method.upper()} · "
            f"{d.amount_usdt:.2f} USDT · ref <code>{d.txn_reference or '-'}</code>"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("approve_dep"))
async def approve_dep(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = (command.args or "").split(maxsplit=1)
    if not args:
        await message.answer("Usage: /approve_dep ID [note]")
        return
    try:
        did = int(args[0])
    except ValueError:
        await message.answer("Bad ID.")
        return
    dep = await deposits_repo.get_deposit(session, did)
    if dep is None or dep.status != "pending":
        await message.answer("Deposit not pending or not found.")
        return
    note = args[1] if len(args) > 1 else ""
    await wallet.credit(
        session, user_id=dep.user_id,
        amount=Decimal(str(dep.amount_usdt)),
        kind="deposit", ref_id=dep.id, note=f"deposit#{dep.id}",
    )
    await deposits_repo.decide_deposit(
        session, deposit=dep, approved=True, admin_id=message.from_user.id, admin_note=note,
    )
    await reward_on_deposit(
        session, depositor_id=dep.user_id, deposit_id=dep.id,
        amount=Decimal(str(dep.amount_usdt)),
    )
    await message.answer(f"Approved #{dep.id} — credited {dep.amount_usdt:.2f} USDT.")
    with contextlib.suppress(Exception):
        await message.bot.send_message(
            dep.user_id,
            f"{pe('check')} <b>Deposit approved</b>\n\nTicket #{dep.id} — {dep.amount_usdt:.2f} USDT credited.",
            parse_mode="HTML",
        )


@router.message(Command("reject_dep"))
async def reject_dep(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = (command.args or "").split(maxsplit=1)
    if not args:
        await message.answer("Usage: /reject_dep ID [reason]")
        return
    try:
        did = int(args[0])
    except ValueError:
        await message.answer("Bad ID.")
        return
    dep = await deposits_repo.get_deposit(session, did)
    if dep is None or dep.status != "pending":
        await message.answer("Deposit not pending or not found.")
        return
    note = args[1] if len(args) > 1 else ""
    await deposits_repo.decide_deposit(
        session, deposit=dep, approved=False, admin_id=message.from_user.id, admin_note=note,
    )
    await message.answer(f"Rejected #{dep.id}.")
    with contextlib.suppress(Exception):
        await message.bot.send_message(
            dep.user_id,
            f"{pe('cross')} <b>Deposit rejected</b>\n\nTicket #{dep.id}\nReason: {note or 'not specified'}",
            parse_mode="HTML",
        )


# ─── Withdrawals ──────────────────────────────────────────────────────────────

@router.message(Command("withdrawals"))
async def list_withdrawals(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    pending = await wd_repo.get_pending_withdrawals(session)
    if not pending:
        await message.answer("No pending withdrawals.")
        return
    lines = []
    for w in pending:
        lines.append(
            f"#{w.id} · user <code>{w.user_id}</code> · {w.method.upper()} · "
            f"{w.amount_usdt:.2f} USDT → <code>{w.address}</code>"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("approve_wd"))
async def approve_wd(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = (command.args or "").split(maxsplit=1)
    if not args:
        await message.answer("Usage: /approve_wd ID [note]")
        return
    try:
        wid = int(args[0])
    except ValueError:
        await message.answer("Bad ID.")
        return
    w = await wd_repo.get_withdrawal(session, wid)
    if w is None or w.status != "pending":
        await message.answer("Not pending or not found.")
        return
    note = args[1] if len(args) > 1 else ""
    # Funds were already held when user submitted the request; just record the decision.
    await wd_repo.decide_withdrawal(
        session, withdrawal=w, approved=True, admin_id=message.from_user.id, admin_note=note,
    )
    session.add(Transaction(
        user_id=w.user_id, kind="withdrawal", amount_usdt=-Decimal(str(w.amount_usdt)),
        ref_id=w.id, note=f"withdrawal#{w.id} approved",
    ))
    await session.commit()
    await message.answer(f"Approved withdrawal #{w.id}.")
    with contextlib.suppress(Exception):
        await message.bot.send_message(
            w.user_id,
            f"{pe('check')} <b>Withdrawal paid</b>\n\nTicket #{w.id} — {w.amount_usdt:.2f} USDT to <code>{w.address}</code>.",
            parse_mode="HTML",
        )


@router.message(Command("reject_wd"))
async def reject_wd(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    args = (command.args or "").split(maxsplit=1)
    if not args:
        await message.answer("Usage: /reject_wd ID [reason]")
        return
    try:
        wid = int(args[0])
    except ValueError:
        await message.answer("Bad ID.")
        return
    w = await wd_repo.get_withdrawal(session, wid)
    if w is None or w.status != "pending":
        await message.answer("Not pending or not found.")
        return
    note = args[1] if len(args) > 1 else ""
    # Refund the held funds
    await wallet.credit(
        session, user_id=w.user_id, amount=Decimal(str(w.amount_usdt)),
        kind="withdrawal_refund", ref_id=w.id,
        note=f"withdrawal#{w.id} rejected: {note}",
    )
    await wd_repo.decide_withdrawal(
        session, withdrawal=w, approved=False, admin_id=message.from_user.id, admin_note=note,
    )
    await message.answer(f"Rejected withdrawal #{w.id} — {w.amount_usdt:.2f} USDT refunded.")
    with contextlib.suppress(Exception):
        await message.bot.send_message(
            w.user_id,
            f"{pe('cross')} <b>Withdrawal rejected</b>\n\nTicket #{w.id} — {w.amount_usdt:.2f} USDT refunded.\n"
            f"Reason: {note or 'not specified'}",
            parse_mode="HTML",
        )


# ─── Users ────────────────────────────────────────────────────────────────────

@router.message(Command("whois"))
async def whois(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int((command.args or "").strip())
    except ValueError:
        await message.answer("Usage: /whois USER_ID")
        return
    u = await get_user(session, uid)
    if u is None:
        await message.answer("Not found.")
        return
    n_orders = int(await session.scalar(
        select(func.count(Order.id)).where(Order.user_id == uid)
    ) or 0)
    await message.answer(
        f"<b>User {u.id}</b> @{u.username or '-'}\n"
        f"Balance: {u.balance_usdt:.2f} USDT\n"
        f"Joined: {u.joined_at.strftime('%Y-%m-%d')}\n"
        f"Orders: {n_orders}\n"
        f"Banned: {u.is_banned}\n"
        f"Referral code: {u.referral_code}",
        parse_mode="HTML",
    )


@router.message(Command("credit"))
async def credit_user(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Usage: /credit USER_ID 10.00 [note]")
        return
    try:
        uid = int(parts[0])
        amt = Decimal(parts[1])
    except (ValueError, InvalidOperation):
        await message.answer("Invalid arguments.")
        return
    note = parts[2] if len(parts) > 2 else "admin credit"
    await wallet.credit(session, user_id=uid, amount=amt, kind="admin_credit", note=note)
    await message.answer(f"Credited {amt:.2f} USDT to {uid}.")


@router.message(Command("debit"))
async def debit_user(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (command.args or "").split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Usage: /debit USER_ID 5.00 [note]")
        return
    try:
        uid = int(parts[0])
        amt = Decimal(parts[1])
    except (ValueError, InvalidOperation):
        await message.answer("Invalid arguments.")
        return
    note = parts[2] if len(parts) > 2 else "admin debit"
    try:
        await wallet.debit(session, user_id=uid, amount=amt, kind="admin_debit", note=note)
    except ValueError as e:
        await message.answer(str(e))
        return
    await message.answer(f"Debited {amt:.2f} USDT from {uid}.")


@router.message(Command("ban"))
async def ban(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int((command.args or "").strip())
    except ValueError:
        await message.answer("Usage: /ban USER_ID")
        return
    u = await get_user(session, uid)
    if u is None:
        await message.answer("Not found.")
        return
    u.is_banned = True
    await session.commit()
    await message.answer(f"Banned {uid}.")


@router.message(Command("unban"))
async def unban(message: Message, command: CommandObject, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int((command.args or "").strip())
    except ValueError:
        await message.answer("Usage: /unban USER_ID")
        return
    u = await get_user(session, uid)
    if u is None:
        await message.answer("Not found.")
        return
    u.is_banned = False
    await session.commit()
    await message.answer(f"Unbanned {uid}.")


# ─── Broadcast ────────────────────────────────────────────────────────────────

@router.message(Command("broadcast"))
async def broadcast_cmd(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer("Send the broadcast message now (text or photo with caption). It will be forwarded to every active user. Send /cancel to abort.")


@router.message(Command("cancel"), AdminStates.waiting_broadcast)
async def broadcast_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Broadcast cancelled.")


@router.message(AdminStates.waiting_broadcast)
async def broadcast_send(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    users = (await session.scalars(select(User).where(User.is_banned.is_(False)))).all()
    sent = 0
    failed = 0
    for u in users:
        if not u.notifications_enabled:
            continue
        try:
            await message.copy_to(chat_id=u.id)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"Broadcast complete. Sent: {sent}. Failed: {failed}.")


# ─── Premium emoji helpers ────────────────────────────────────────────────────

@router.message(Command("getemoji"))
async def get_emoji(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    target = message.reply_to_message or message
    entities = (target.entities or []) + (target.caption_entities or [])
    found = []
    for e in entities:
        if e.type == "custom_emoji" and e.custom_emoji_id:
            found.append(e.custom_emoji_id)
    if not found:
        await message.answer(
            "Reply to a message that contains <b>premium custom emojis</b> with /getemoji to capture their IDs.",
            parse_mode="HTML",
        )
        return
    lines = "\n".join(f"<code>{eid}</code>" for eid in found)
    await message.answer(
        f"Found custom_emoji_id(s):\n{lines}\n\n"
        "Add them to <code>assets/premium_emojis.json</code> and run /reload_emojis.",
        parse_mode="HTML",
    )


@router.message(Command("reload_emojis"))
async def reload_emojis(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    reload_map()
    await message.answer("Premium emoji map reloaded.")


@router.message(Command("stats"))
async def stats(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    n_users = int(await session.scalar(select(func.count(User.id))) or 0)
    n_orders = int(await session.scalar(select(func.count(Order.id))) or 0)
    n_dep_pending = int(await session.scalar(
        select(func.count(Deposit.id)).where(Deposit.status == "pending")
    ) or 0)
    n_wd_pending = int(await session.scalar(
        select(func.count(Withdrawal.id)).where(Withdrawal.status == "pending")
    ) or 0)
    n_stock = int(await session.scalar(
        select(func.count(StockItem.id)).where(StockItem.status == "available")
    ) or 0)
    revenue = Decimal(str(await session.scalar(
        select(func.coalesce(func.sum(Order.price_usdt), 0))
    ) or 0))
    last_order = await session.scalar(select(Order).order_by(desc(Order.id)).limit(1))
    await message.answer(
        f"<b>Bot stats</b>\n\n"
        f"Users: {n_users}\n"
        f"Orders: {n_orders}\n"
        f"Revenue: {revenue:.2f} USDT\n"
        f"Available stock: {n_stock}\n"
        f"Pending deposits: {n_dep_pending}\n"
        f"Pending withdrawals: {n_wd_pending}\n"
        f"Last order id: {last_order.id if last_order else '-'}",
        parse_mode="HTML",
    )
