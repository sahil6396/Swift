from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Deposit


async def create_deposit(
    session: AsyncSession,
    *,
    user_id: int,
    method: str,
    amount_usdt: Decimal,
    txn_reference: str,
    proof_file_id: str | None,
    note: str = "",
) -> Deposit:
    dep = Deposit(
        user_id=user_id,
        method=method,
        amount_usdt=amount_usdt,
        txn_reference=txn_reference,
        proof_file_id=proof_file_id,
        note=note,
        status="pending",
    )
    session.add(dep)
    await session.commit()
    await session.refresh(dep)
    return dep


async def total_deposited(session: AsyncSession, user_id: int) -> Decimal:
    n = await session.scalar(
        select(func.coalesce(func.sum(Deposit.amount_usdt), 0)).where(
            Deposit.user_id == user_id, Deposit.status == "approved"
        )
    )
    return Decimal(str(n or 0))


async def get_pending_deposits(session: AsyncSession, limit: int = 50) -> list[Deposit]:
    return list((await session.scalars(
        select(Deposit).where(Deposit.status == "pending").order_by(Deposit.id).limit(limit)
    )).all())


async def get_deposit(session: AsyncSession, deposit_id: int) -> Deposit | None:
    return await session.get(Deposit, deposit_id)


async def decide_deposit(
    session: AsyncSession,
    *,
    deposit: Deposit,
    approved: bool,
    admin_id: int,
    admin_note: str = "",
) -> Deposit:
    deposit.status = "approved" if approved else "rejected"
    deposit.admin_note = admin_note
    deposit.decided_by = admin_id
    deposit.decided_at = datetime.now(timezone.utc)
    await session.commit()
    return deposit


async def recent_deposits(session: AsyncSession, user_id: int, limit: int = 10) -> list[Deposit]:
    return list((await session.scalars(
        select(Deposit).where(Deposit.user_id == user_id)
        .order_by(desc(Deposit.id)).limit(limit)
    )).all())
