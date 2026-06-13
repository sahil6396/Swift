"""Referral commission logic."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..repositories import orders as orders_repo
from ..repositories import referrals as ref_repo
from ..repositories.users import get_user


async def reward_on_purchase(
    session: AsyncSession,
    *,
    buyer_id: int,
    order_id: int,
    price: Decimal,
) -> None:
    """Pay 2% commission to the buyer's referrer (if any). Plus first-purchase bonus."""
    s = get_settings()
    buyer = await get_user(session, buyer_id)
    if buyer is None or not buyer.referred_by:
        return
    referrer_id = buyer.referred_by

    # 2% commission on every purchase
    commission = (price * (s.referral_commission_pct / Decimal("100"))).quantize(Decimal("0.01"))
    if commission > 0:
        await ref_repo.add_earning(
            session,
            referrer_id=referrer_id,
            source_user_id=buyer_id,
            source_event="purchase",
            amount=commission,
            source_ref_id=order_id,
        )

    # First-purchase bonus
    n_orders = await orders_repo.total_orders(session, buyer_id)
    if n_orders == 1 and s.referral_first_purchase_bonus_usdt > 0:
        await ref_repo.add_earning(
            session,
            referrer_id=referrer_id,
            source_user_id=buyer_id,
            source_event="first_purchase_bonus",
            amount=Decimal(str(s.referral_first_purchase_bonus_usdt)),
            source_ref_id=order_id,
        )


async def reward_on_deposit(
    session: AsyncSession,
    *,
    depositor_id: int,
    deposit_id: int,
    amount: Decimal,
) -> None:
    s = get_settings()
    depositor = await get_user(session, depositor_id)
    if depositor is None or not depositor.referred_by:
        return
    commission = (amount * (s.referral_commission_pct / Decimal("100"))).quantize(Decimal("0.01"))
    if commission <= 0:
        return
    await ref_repo.add_earning(
        session,
        referrer_id=depositor.referred_by,
        source_user_id=depositor_id,
        source_event="deposit",
        amount=commission,
        source_ref_id=deposit_id,
    )
