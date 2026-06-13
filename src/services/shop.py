"""Buy flow: deduct balance, atomically pop one stock item, write order, pay referral."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Order, Product, Transaction
from ..repositories import orders as orders_repo
from ..repositories import products as products_repo
from ..repositories.users import get_user
from .referral import reward_on_purchase


class BuyError(Exception):
    pass


class InsufficientBalance(BuyError):
    pass


class OutOfStock(BuyError):
    pass


@dataclass
class BuyResult:
    order: Order
    product: Product
    payload: str


async def buy_product(
    session: AsyncSession, *, user_id: int, product_id: int
) -> BuyResult:
    product = await products_repo.get_product(session, product_id)
    if product is None or not product.is_active:
        raise BuyError("Product not found.")

    user = await get_user(session, user_id)
    if user is None:
        raise BuyError("User not found.")

    if Decimal(str(user.balance_usdt)) < Decimal(str(product.price_usdt)):
        raise InsufficientBalance(
            f"Need {product.price_usdt:.2f} USDT, have {user.balance_usdt:.2f} USDT."
        )

    item = await products_repo.pop_one_stock_item(session, product_id)
    if item is None:
        raise OutOfStock("This product is out of stock.")

    user.balance_usdt = Decimal(str(user.balance_usdt)) - Decimal(str(product.price_usdt))
    order = await orders_repo.create_order(session, user_id=user_id, product=product, stock_item=item)

    session.add(Transaction(
        user_id=user_id,
        kind="purchase",
        amount_usdt=-Decimal(str(product.price_usdt)),
        ref_id=order.id,
        note=f"Purchase: {product.display_name}",
    ))
    await session.commit()

    # Referral commission (separate transaction).
    await reward_on_purchase(
        session, buyer_id=user_id, order_id=order.id, price=Decimal(str(product.price_usdt))
    )

    return BuyResult(order=order, product=product, payload=item.payload)
