"""Deposit flow: amount → method → instructions → submit proof (FSM)."""
from __future__ import annotations

import contextlib
import logging
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..repositories import deposits as deposits_repo
from ..repositories import referrals as ref_repo
from ..repositories.users import get_user
from ..ui import keyboards as kb
from ..ui import texts
from ..ui.editor import render, render_from_callback
from .states import DepositStates

router = Router(name="deposit")
log = logging.getLogger(__name__)


async def _show_deposit_screen(cb: CallbackQuery, session: AsyncSession) -> None:
    s = get_settings()
    user = await get_user(session, cb.from_user.id)
    summary = await ref_repo.referral_summary(session, cb.from_user.id)
    text = texts.deposit(
        balance=Decimal(str(user.balance_usdt)) if user else Decimal("0"),
        referral_available=summary["available"],
        referral_total_earned=summary["earned_total"],
        binance_uid=s.binance_uid,
        upi_id=s.upi_id,
    )
    await render_from_callback(
        cb, session=session, text=text,
        keyboard=kb.deposit_kb(has_referral_balance=summary["available"] > 0),
    )


@router.callback_query(F.data == kb.CB_DEPOSIT)
async def show_deposit(cb: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await _show_deposit_screen(cb, session)
    await cb.answer()


@router.callback_query(F.data.startswith(f"{kb.CB_DEPOSIT_AMOUNT}:"))
async def deposit_amount(cb: CallbackQuery, session: AsyncSession) -> None:
    cents = int(cb.data.split(":")[2])
    amount = (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))
    await render_from_callback(
        cb, session=session,
        text=texts.deposit_method_choose(amount=amount),
        keyboard=kb.deposit_method_kb(amount_cents=cents),
    )
    await cb.answer()


@router.callback_query(F.data == kb.CB_DEPOSIT_CUSTOM)
async def deposit_custom(cb: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await render_from_callback(
        cb, session=session,
        text=texts.deposit_custom_prompt(),
        keyboard=kb.cancel_to_main_kb(),
    )
    await state.set_state(DepositStates.waiting_custom_amount)
    await cb.answer()


@router.message(DepositStates.waiting_custom_amount)
async def deposit_custom_input(message: Message, session: AsyncSession, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    user = await get_user(session, message.from_user.id)
    if text == "cancel":
        await state.clear()
        await _show_deposit_msg(message, session)
        with contextlib.suppress(Exception):
            await message.delete()
        return
    try:
        amount = Decimal(text).quantize(Decimal("0.01"))
        if amount < Decimal("1"):
            raise InvalidOperation()
    except (InvalidOperation, ValueError):
        await message.answer(
            f"{texts.pe('warning')} Enter a valid amount in USDT (e.g. <code>15</code> or <code>27.50</code>). "
            "Send <code>cancel</code> to abort.",
            parse_mode="HTML",
        )
        return
    cents = int(amount * 100)
    # Edit the menu message to method picker
    if user and user.last_chat_id and user.last_menu_message_id:
        await render(
            bot=message.bot, session=session,
            user_id=user.id, chat_id=user.last_chat_id,
            text=texts.deposit_method_choose(amount=amount),
            keyboard=kb.deposit_method_kb(amount_cents=cents),
            message_id=user.last_menu_message_id,
        )
    await state.clear()
    with contextlib.suppress(Exception):
        await message.delete()


async def _show_deposit_msg(message: Message, session: AsyncSession) -> None:
    """Re-render deposit screen on the saved menu message id."""
    s = get_settings()
    user = await get_user(session, message.from_user.id)
    if user is None or user.last_menu_message_id is None or user.last_chat_id is None:
        return
    summary = await ref_repo.referral_summary(session, user.id)
    await render(
        bot=message.bot, session=session,
        user_id=user.id, chat_id=user.last_chat_id,
        text=texts.deposit(
            balance=Decimal(str(user.balance_usdt)),
            referral_available=summary["available"],
            referral_total_earned=summary["earned_total"],
            binance_uid=s.binance_uid,
            upi_id=s.upi_id,
        ),
        keyboard=kb.deposit_kb(has_referral_balance=summary["available"] > 0),
        message_id=user.last_menu_message_id,
    )


@router.callback_query(F.data.startswith(f"{kb.CB_DEPOSIT_METHOD}:"))
async def deposit_method(cb: CallbackQuery, session: AsyncSession) -> None:
    _, _, method, cents_str = cb.data.split(":")
    cents = int(cents_str)
    amount = (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))
    s = get_settings()
    if method == "binance":
        text = texts.deposit_instructions_binance(amount=amount, uid=s.binance_uid)
    else:
        text = texts.deposit_instructions_upi(amount=amount, upi_id=s.upi_id, upi_name=s.upi_name)
    await render_from_callback(
        cb, session=session, text=text,
        keyboard=kb.deposit_submit_kb(method=method, amount_cents=cents),
    )
    await cb.answer()


@router.callback_query(F.data.startswith(f"{kb.CB_DEPOSIT_SUBMIT}:"))
async def deposit_submit_start(cb: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    _, _, method, cents_str = cb.data.split(":")
    cents = int(cents_str)
    amount = (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))
    await state.set_state(DepositStates.waiting_proof)
    await state.update_data(method=method, amount_cents=cents)
    await render_from_callback(
        cb, session=session,
        text=texts.deposit_ask_proof(method=method, amount=amount),
        keyboard=kb.cancel_to_main_kb(),
    )
    await cb.answer()


@router.message(DepositStates.waiting_proof)
async def deposit_proof_received(message: Message, session: AsyncSession, state: FSMContext) -> None:
    body = (message.text or message.caption or "").strip()
    if body.lower() == "cancel":
        await state.clear()
        await _show_deposit_msg(message, session)
        with contextlib.suppress(Exception):
            await message.delete()
        return
    data = await state.get_data()
    method = data.get("method", "binance")
    amount = (Decimal(data.get("amount_cents", 0)) / Decimal(100)).quantize(Decimal("0.01"))
    txn_ref = body
    proof_file_id = None
    if message.photo:
        proof_file_id = message.photo[-1].file_id
    elif message.document:
        proof_file_id = message.document.file_id

    if not txn_ref and not proof_file_id:
        await message.answer(
            f"{texts.pe('warning')} Please send your transaction ID, UTR, or a screenshot. "
            "Send <code>cancel</code> to abort.",
            parse_mode="HTML",
        )
        return

    dep = await deposits_repo.create_deposit(
        session,
        user_id=message.from_user.id,
        method=method,
        amount_usdt=amount,
        txn_reference=txn_ref,
        proof_file_id=proof_file_id,
    )
    await state.clear()
    user = await get_user(session, message.from_user.id)
    if user and user.last_chat_id and user.last_menu_message_id:
        await render(
            bot=message.bot, session=session,
            user_id=user.id, chat_id=user.last_chat_id,
            text=texts.deposit_submitted(deposit_id=dep.id),
            keyboard=kb.main_menu_kb(),
            message_id=user.last_menu_message_id,
        )
    with contextlib.suppress(Exception):
        await message.delete()

    # Notify admins
    await _notify_admins_new_deposit(message.bot, session, dep, message.from_user.username)


async def _notify_admins_new_deposit(bot, session: AsyncSession, dep, username: str | None) -> None:
    s = get_settings()
    text = (
        f"{texts.pe('coin')} <b>New deposit submitted</b>\n\n"
        f"User: <code>{dep.user_id}</code> @{username or '-'}\n"
        f"Method: <b>{dep.method.upper()}</b>\n"
        f"Amount: <b>{dep.amount_usdt:.2f} USDT</b>\n"
        f"Ref: <code>{dep.txn_reference or '-'}</code>\n"
        f"Ticket #: <code>{dep.id}</code>\n\n"
        f"Approve: <code>/approve_dep {dep.id}</code>\n"
        f"Reject:  <code>/reject_dep {dep.id} reason</code>"
    )
    for admin_id in s.admin_ids:
        with contextlib.suppress(Exception):
            await bot.send_message(admin_id, text, parse_mode="HTML")
            if dep.proof_file_id:
                with contextlib.suppress(Exception):
                    await bot.send_photo(admin_id, dep.proof_file_id,
                                         caption=f"Proof for deposit #{dep.id}")


@router.callback_query(F.data == kb.CB_DEPOSIT_TRANSFER_REF)
async def transfer_ref_from_deposit(cb: CallbackQuery, session: AsyncSession) -> None:
    moved = await ref_repo.transfer_available_to_wallet(session, cb.from_user.id)
    if moved <= 0:
        await cb.answer("Nothing to transfer.", show_alert=True)
        await _show_deposit_screen(cb, session)
        return
    await cb.answer(f"+{moved:.2f} USDT moved to wallet")
    await _show_deposit_screen(cb, session)
