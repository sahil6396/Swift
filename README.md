# Baba Swift Bot

A clone of the Baba-Swift-style Telegram shop bot — products, manual deposits
(Binance UID + UPI), wallet, referral system (2% + first-purchase bonus),
withdrawals, in-bot admin commands, and a localhost-only admin web dashboard.

Built with **Python 3.11+ / aiogram v3 / SQLite / FastAPI**, designed to be run
on a Windows machine straight from `cmd.exe` or PowerShell — no Docker, no
external services beyond Telegram itself.

---

## Key features

- **Single-message UX.** Every button press *edits the same menu message* —
  the bot never spams new messages. Falls back to a fresh send if the original
  is deleted or too old.
- **Premium custom emojis everywhere.** In message bodies via Telegram's
  `<tg-emoji>` HTML tag and on inline keyboard buttons via Bot API 9.4's
  `icon_custom_emoji_id` field. Both fall back to plain unicode glyphs when
  the user's client can't render them. Requires the bot owner to hold a
  Telegram Premium subscription — set `PREMIUM_BUTTON_ICONS=false` if not.
- **Symmetric button colours** via Bot API 9.4's `style` field: navigation
  buttons are blue (`primary`), positive commits like *Buy* / *Confirm* /
  *Submit* / *Generate token* are green (`success`), and destructive actions
  like *Cancel* / *Revoke* / *Out of stock* are red (`danger`). Disable with
  `BUTTON_STYLES_ENABLED=false`.
- **Back / Home buttons** on every sub-screen.
- **Manual deposit flow.** Show Binance UID or UPI ID → user submits txn ID or
  proof → admin approves via in-bot command or web dashboard → wallet credited
  → referral commission paid out.
- **Atomic stock pop.** Each product has a stock pool of credentials
  (`email:pass`, license keys, anything plain-text). Buying pops one item
  inside a transaction so two users can't claim the same item.
- **Referral system.** Configurable commission (default **2 %**) on every
  deposit and purchase, plus a one-time **$0.50** first-purchase bonus.
  Referrers can transfer earned balance into their wallet.
- **Withdrawal FSM** with admin approval and automatic refund on rejection.
- **In-bot admin commands** (`/admin` lists them) plus an optional
  **localhost web dashboard** at `http://127.0.0.1:8088`.
- **Manage products without touching code** — add / edit / disable / restock
  via either Telegram commands or the web dashboard.

---

## Quick start

> Requires **Python 3.11 or newer**. On Windows install from
> <https://www.python.org/downloads/> and tick *"Add python.exe to PATH"*.

```sh
# 1. Get the code
cd baba-swift-bot

# 2. (Recommended) create + activate a virtual environment
python -m venv .venv
# Windows cmd:        .venv\Scripts\activate.bat
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux / macOS:      source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env       # Windows: copy .env.example .env
# Edit .env: set BOT_TOKEN, ADMIN_IDS, BINANCE_UID, UPI_ID, DASHBOARD_PASSWORD

# 5. Run the bot
python bot.py

# 6. (Optional) in a separate terminal, run the admin web dashboard
python dashboard.py
# then open http://127.0.0.1:8088 and log in with DASHBOARD_PASSWORD
```

That's it — `bot.py` starts long polling and `dashboard.py` starts the
localhost-only admin panel. Both can run side-by-side. Stop either with
`Ctrl+C`.

If PowerShell complains about activating the venv:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

## Configuration (`.env`)

Copy `.env.example` to `.env` and fill in:

| Variable                | Required | Default               | Notes |
|-------------------------|----------|-----------------------|-------|
| `BOT_TOKEN`             | yes      | —                     | From [@BotFather](https://t.me/BotFather). **Rotate the one you shared in chat.** |
| `ADMIN_IDS`             | yes      | —                     | Comma-separated Telegram user IDs that have admin powers. Get yours from `@userinfobot`. |
| `BOT_USERNAME`          | no       | auto-detected         | Used to build referral links. Auto-fetched via `getMe` if blank. |
| `SHOP_NAME`             | no       | `Baba Swift Shop`       | Displayed in headers. |
| `SUPPORT_USERNAME`      | no       | `babaswiftbot`        | Telegram username (no `@`) the *Support* button links to. |
| `BINANCE_UID`           | yes      | —                     | Your Binance UID for manual deposits. |
| `UPI_ID`                | yes      | —                     | Your UPI ID for manual deposits. |
| `UPI_NAME`              | no       | `Baba Swift Shop`       | Holder name shown next to the UPI ID. |
| `DATABASE_URL`          | no       | `sqlite+aiosqlite:///./data/bot.db` | Override only if you want Postgres. |
| `DASHBOARD_HOST`        | no       | `127.0.0.1`           | Don't change — keep it local. |
| `DASHBOARD_PORT`        | no       | `8088`                | |
| `DASHBOARD_PASSWORD`    | yes      | (sample)              | **Change** before exposing the dashboard. |
| `DASHBOARD_SESSION_SECRET` | yes   | (sample)              | Random string used to sign session cookies. |
| `REFERRAL_COMMISSION_PCT` | no     | `2.0`                 | Commission % on every deposit and purchase. |
| `REFERRAL_FIRST_PURCHASE_BONUS_USDT` | no | `0.50`            | One-time bonus to the referrer when the referee first buys. |
| `WITHDRAW_MIN_USDT`     | no       | `2.0`                 | Minimum withdrawal. |
| `WITHDRAW_MAX_USDT`     | no       | `1000.0`              | Maximum withdrawal. |
| `LOG_LEVEL`             | no       | `INFO`                | `DEBUG` while developing. |
| `PREMIUM_BUTTON_ICONS`  | no       | `true`                | Render premium emojis as button icons (Bot API 9.4 `icon_custom_emoji_id`). Requires Premium on the bot owner. Set to `false` to fall back to unicode glyphs in button text. |
| `BUTTON_STYLES_ENABLED` | no       | `true`                | Apply Bot API 9.4 button colours (`primary` / `success` / `danger`). Set to `false` for the client default everywhere. |

---

## Admin commands (in-bot)

Send these from a Telegram account whose ID is listed in `ADMIN_IDS`:

```
/admin                          # show this help
/products                       # list products + stock counts
/addproduct slug|Name|emoji|duration|price
/setprice slug 24.99
/setactive slug on|off
/setdesc slug Description text...
/addstock slug                  # then send a .txt file with one credential per line
/stock slug                     # available stock for the product

/deposits                       # list pending deposits
/approve_dep ID [note]
/reject_dep ID reason

/withdrawals                    # list pending withdrawals
/approve_wd ID [note]
/reject_wd ID reason

/whois USER_ID
/credit USER_ID 10.00 [note]
/debit  USER_ID 5.00 [note]
/ban USER_ID
/unban USER_ID

/broadcast                      # then send the message to broadcast
/getemoji                       # reply to a message with premium emojis to capture their IDs
/reload_emojis                  # re-read assets/premium_emojis.json
/stats                          # bot stats
```

### Premium custom emojis

Telegram premium custom emojis can only appear in **message bodies**, not in
inline-keyboard button labels. The bot loads emoji IDs from
[`assets/premium_emojis.json`](assets/premium_emojis.json) — every entry has a
`fallback` (a regular unicode emoji shown to non-premium users) and an
optional `id`.

To capture a premium emoji's ID:

1. Send a message containing the premium emoji to the bot from your premium
   account.
2. Reply to that message with `/getemoji`.
3. The bot prints the `custom_emoji_id`. Paste it into the matching slot in
   `assets/premium_emojis.json`.
4. Run `/reload_emojis` (no restart needed).

---

## Web dashboard

Bind only to `127.0.0.1` (the default). It is **not safe** to expose this on
the public internet — there's a single shared password and no rate limiting.

URL: <http://127.0.0.1:8088>

Pages:
- **Dashboard** — high-level stats
- **Products** — add / edit products, upload stock (paste lines or `.txt`)
- **Deposits** — approve / reject pending deposits
- **Withdrawals** — approve / reject pending withdrawals
- **Orders** — recent fulfillment history with delivered payload
- **Users** — search, ban, manually credit / debit a wallet

All changes apply instantly — no need to restart the bot.

---

## Architecture

```
src/
├── config.py            # pydantic-settings
├── main.py              # bot entrypoint (long polling)
├── utils.py             # referral / api token generators
├── db/
│   ├── base.py          # SQLAlchemy declarative base
│   ├── models.py        # User, Product, StockItem, Order, Deposit,
│   │                    # Withdrawal, ReferralEarning, Transaction, ApiToken
│   ├── session.py       # async engine + session factory + init_db
│   └── seed.py          # initial products from the screenshots
├── repositories/        # thin async DB CRUD per entity
├── services/            # business logic (shop, wallet, referral)
├── ui/
│   ├── editor.py        # safe edit_message_text → fallback to send
│   ├── emoji.py         # premium custom-emoji helper (pe / fb)
│   ├── keyboards.py     # every InlineKeyboardMarkup
│   └── texts.py         # every HTML message body
├── handlers/            # aiogram routers (start, shop, deposit, profile,
│   │                    # support, refer, admin)
├── middleware/
│   ├── db.py            # injects an AsyncSession per update
│   └── throttle.py      # rate-limits callback queries
└── admin_dashboard/
    ├── server.py        # FastAPI app
    └── templates/       # Jinja2 HTML
```

The single-message UX is implemented in
[`src/ui/editor.py`](src/ui/editor.py): every menu render goes through
`render(...)`, which tries `edit_message_text` first and only sends a new
message as a fallback. The `last_menu_message_id` is persisted on the user
row, so even text-input flows (deposit custom amount, withdrawal address)
edit the original menu instead of replying inline.

---

## Database

SQLite by default — file lives at `./data/bot.db` (auto-created on first
run). To switch to Postgres, set:

```
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
```

Schema is created automatically via `Base.metadata.create_all`. For real
production migrations, plug in Alembic.

---

## Testing the bot end-to-end

1. `python bot.py` — long polling begins.
2. Open Telegram, search for `@<your bot username>`, press **Start**.
3. Tap each main-menu button — every press should *edit* the same message.
4. Tap **Refer & Earn** → **Copy Referral Link**. Open the resulting link in
   a second Telegram account → both accounts now share a referral
   relationship.
5. Tap **Deposit** → `$10` → **Binance UID** → **I've paid** → send any txn
   ID. The admin account receives `💰 New deposit submitted` with `/approve_dep`
   and `/reject_dep` shortcuts.
6. Approve → the user's balance goes up; the referrer earns 2 %.
7. Add stock to a product (`/addstock cursor_pro_12m` → send `.txt`), then
   buy from the user account.

---

## Security notes

- **Rotate your `BOT_TOKEN`** if you've ever pasted it in plaintext (e.g. in
  this repo's chat or a screenshot). Use `/revoke` in @BotFather.
- The dashboard binds to localhost only. Don't put it behind nginx without
  adding TLS + IP allowlisting + a stronger auth layer.
- Don't commit `.env` — it's gitignored.
- The bot is **not** a payment processor: deposits and withdrawals are
  manually confirmed by you. Nothing happens automatically with crypto/UPI.

---

## Licence

MIT — do whatever you want, but credit is appreciated.
