"""Shop list, product detail, buy flow."""
from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories import products as products_repo
from ..repositories.users import get_user
from ..services.shop import BuyError, InsufficientBalance, OutOfStock, buy_product
from ..ui import keyboards as kb
from ..ui import texts
from ..ui.editor import render_from_callback
from ..ui.emoji import find_emoji_id

router = Router(name="shop")
log = logging.getLogger(__name__)


@router.callback_query(F.data.in_({kb.CB_SHOP, kb.CB_REFRESH_SHOP}))
async def show_shop(cb: CallbackQuery, session: AsyncSession) -> None:
    items = await products_repo.list_active_products_with_stock(session)
    if not items:
        await render_from_callback(cb, session=session, text=texts.shop_empty(),
                                   keyboard=kb.main_menu_kb())
        await cb.answer()
        return
    # Per-product `emoji_id` column wins, but fall back to the registry
    # so admins who populated `assets/premium_emojis.json` get premium
    # button icons without having to /setemoji every slug.
    rows = [
        (
            p.id,
            p.display_name,
            p.emoji,
            p.emoji_id or find_emoji_id(p.emoji),
            p.duration_label,
            stock,
        )
        for p, stock in items
    ]
    await render_from_callback(
        cb, session=session,
        text=texts.shop_header(total=len(items)),
        keyboard=kb.shop_list_kb(rows),
    )
    if cb.data == kb.CB_REFRESH_SHOP:
        await cb.answer("Refreshed")
    else:
        await cb.answer()


@router.callback_query(F.data.startswith(f"{kb.CB_PRODUCT}:"))
async def show_product(cb: CallbackQuery, session: AsyncSession) -> None:
    pid = int(cb.data.split(":")[2])
    product = await products_repo.get_product(session, pid)
    if product is None or not product.is_active:
        await cb.answer("Product not available.", show_alert=True)
        return
    stock = await products_repo.count_available_stock(session, pid)
    await render_from_callback(
        cb, session=session,
        text=texts.product_detail(
            name=product.display_name,
            emoji=product.emoji,
            emoji_id=product.emoji_id or find_emoji_id(product.emoji),
            duration=product.duration_label,
            price=Decimal(str(product.price_usdt)),
            description=product.description,
            stock=stock,
        ),
        keyboard=kb.product_detail_kb(product.id, can_buy=stock > 0),
    )
    await cb.answer()


@router.callback_query(F.data.startswith(f"{kb.CB_BUY}:"))
async def buy_confirm(cb: CallbackQuery, session: AsyncSession) -> None:
    pid = int(cb.data.split(":")[2])
    product = await products_repo.get_product(session, pid)
    user = await get_user(session, cb.from_user.id)
    if product is None or user is None:
        await cb.answer("Unavailable.", show_alert=True)
        return
    balance = Decimal(str(user.balance_usdt))
    price = Decimal(str(product.price_usdt))
    if balance < price:
        await render_from_callback(
            cb, session=session,
            text=texts.buy_insufficient(price=price, balance=balance),
            keyboard=kb.product_detail_kb(product.id, can_buy=True),
        )
        await cb.answer()
        return
    await render_from_callback(
        cb, session=session,
        text=texts.buy_confirm(name=product.display_name, price=price, balance=balance),
        keyboard=kb.buy_confirm_kb(product.id),
    )
    await cb.answer()


@router.callback_query(F.data.startswith(f"{kb.CB_BUY_CONFIRM}:"))
async def buy_execute(cb: CallbackQuery, session: AsyncSession) -> None:
    pid = int(cb.data.split(":")[2])
    try:
        result = await buy_product(session, user_id=cb.from_user.id, product_id=pid)
    except InsufficientBalance:
        user = await get_user(session, cb.from_user.id)
        product = await products_repo.get_product(session, pid)
        if user and product:
            await render_from_callback(
                cb, session=session,
                text=texts.buy_insufficient(
                    price=Decimal(str(product.price_usdt)),
                    balance=Decimal(str(user.balance_usdt)),
                ),
                keyboard=kb.product_detail_kb(pid, can_buy=True),
            )
        await cb.answer("Insufficient balance.", show_alert=True)
        return
    except OutOfStock:
        await cb.answer("Just sold out.", show_alert=True)
        product = await products_repo.get_product(session, pid)
        if product is not None:
            await render_from_callback(
                cb, session=session,
                text=texts.product_detail(
                    name=product.display_name, emoji=product.emoji,
                    emoji_id=product.emoji_id or find_emoji_id(product.emoji),
                    duration=product.duration_label,
                    price=Decimal(str(product.price_usdt)),
                    description=product.description, stock=0,
                ),
                keyboard=kb.product_detail_kb(pid, can_buy=False),
            )
        return
    except BuyError as e:
        await cb.answer(str(e), show_alert=True)
        return

    await render_from_callback(
        cb, session=session,
        text=texts.buy_success(
            name=result.product.display_name,
            payload=result.payload,
            order_id=result.order.id,
        ),
        keyboard=kb.order_detail_kb(),
    )
    await cb.answer("Purchase complete!")
