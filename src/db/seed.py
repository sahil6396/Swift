"""Seed initial product list (taken from the Baba Swift Shop screenshots)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Product

# (slug, name, emoji, duration, default_price, sort_order)
INITIAL_PRODUCTS: list[tuple[str, str, str, str, str, int]] = [
    ("linkedin_career_3m",       "Linkedin Career (New User)", "💼", "3m",  "9.99",  10),
    ("cursor_pro_12m",           "Cursor Pro",                 "🖱️", "12m", "29.99", 20),
    ("supabase_pro_12m",         "Supabase Pro",               "🗄️", "12m", "24.99", 30),
    ("canva_business_12m",       "Canva Business",             "🎨", "12m", "19.99", 40),
    ("replit_core_12m",          "Replit Core",                "🟧", "12m", "24.99", 50),
    ("n8n_starter_12m",          "n8n Starter",                "🔗", "12m", "14.99", 60),
    ("coursera_plus_12m",        "Coursera Plus",              "🎓", "12m", "39.99", 70),
    ("notion_business_12m",      "Notion Business",            "📒", "12m", "24.99", 80),
    ("elevenlabs_creator_1m",    "ElevenLabs Creator",         "🎙️", "1m",  "5.99",  90),
    ("elevenlabs_creator_12m",   "ElevenLabs Creator",         "🎙️", "12m", "29.99", 91),
    ("elevenlabs_creator_acc_12m","ElevenLabs Creator Account","🎙️", "12m", "29.99", 92),
    ("google_ai_pro_12m",        "Google AI Pro",              "🤖", "12m", "34.99", 100),
    ("chatprd_pro_12m",          "ChatPRD Pro",                "💬", "12m", "14.99", 110),
    ("framer_pro_12m",           "Framer Pro",                 "🎬", "12m", "24.99", 120),
    ("granola_business_12m",     "Granola Business",           "🌀", "12m", "24.99", 130),
    ("gumloop_pro_12m",          "Gumloop Pro",                "🟢", "12m", "19.99", 140),
    ("intercom_advanced_12m",    "Intercom Advanced",          "💭", "12m", "29.99", 150),
    ("linear_business_12m",      "Linear Business",            "📐", "12m", "24.99", 160),
    ("magic_patterns_12m",       "Magic Patterns",             "✨", "12m", "19.99", 170),
    ("posthog_scale_12m",        "PostHog Scale",              "📊", "12m", "29.99", 180),
    ("warp_build_12m",           "Warp Build",                 "⚡", "12m", "19.99", 190),
]


async def seed_products(session: AsyncSession) -> int:
    """Insert any products that are missing. Returns number of newly inserted rows."""
    inserted = 0
    for slug, name, emoji, duration, price, sort_order in INITIAL_PRODUCTS:
        existing = await session.scalar(select(Product).where(Product.slug == slug))
        if existing is not None:
            continue
        session.add(
            Product(
                slug=slug,
                display_name=name,
                emoji=emoji,
                duration_label=duration,
                price_usdt=Decimal(price),
                sort_order=sort_order,
                is_active=True,
                description="",
                delivery_type="stock_pool",
            )
        )
        inserted += 1
    await session.commit()
    return inserted
