# Baba Swift Bot — Owner / Admin Manual

Everything you need to publish, run, and manage the bot **without touching code**.

---

## 0. Before you publish — 3-minute checklist

1. **Rotate the bot token** (the one you pasted in chat is exposed):
   - Open [@BotFather](https://t.me/BotFather) → `/revoke` → pick this bot →
     copy the **new** token.
   - Open `.env` → replace the `BOT_TOKEN=` value with the new token.
2. **Set your real payment destinations** in `.env`:
   - `BINANCE_UID=<your real UID>`
   - `UPI_ID=<your real UPI>` (e.g. `yourname@oksbi`)
   - `UPI_NAME=<the name your UPI is registered under>`
3. (Optional) **Set your shop branding** in `.env`:
   - `SHOP_NAME=Whatever you want`
   - `SUPPORT_USERNAME=YourSupportUsername` (no `@`)
4. Save `.env`. Restart the bot if it's already running (`Ctrl+C` then
   `python bot.py` again).

That's it — the bot is now ready for your channels.

---

## 1. Run it

Open `cmd.exe` (or PowerShell) inside the `baba-swift-bot` folder.

**First time only:**

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Every time you want to start it:**

```
.venv\Scripts\activate
python bot.py
```

The bot will print:
```
Bot @<your_bot_username> ready (id=...). Starting long polling…
```
Leave that window open — the bot stops when you close it.

**Optional: admin web dashboard** (in a *second* terminal):

```
.venv\Scripts\activate
python dashboard.py
```

Then open <http://127.0.0.1:8088> in your browser and log in with
`DASHBOARD_PASSWORD` from `.env`. The dashboard does the same things as the
in-bot admin commands but with forms instead of typing slash commands.

> Run `python bot.py` and `python dashboard.py` **at the same time** in two
> separate terminals. They are two separate processes; the bot does Telegram,
> the dashboard does HTTP.

---

## 2. What your users see

Every user sees the same flow:

1. They tap your bot's **Start** button → the main menu appears with 5 buttons.
2. **Shop** — list of products with stock counts. Tap a product → see the
   description and price → tap **Buy now** → confirm. The credentials are
   delivered instantly inside the bot.
3. **Deposit** — pick a preset amount or type a custom one → choose Binance
   UID or UPI → see your payment instructions → after paying, tap
   *I've paid — submit proof* → send the transaction ID or screenshot.
4. **My Profile** — wallet balance, order history, withdraw, notification
   toggle, developer API token.
5. **Support** — opens a chat with your support username.
6. **Refer & Earn** — referral stats, share link, transfer earnings to wallet.

The whole UI lives in **one chat message** that updates in place — no
spammy new messages.

User-facing slash commands (also shown in Telegram's command suggestions):

| Command  | What it does                        |
|----------|-------------------------------------|
| `/start` | Open / re-open the main menu        |
| `/menu`  | Same as `/start`                    |
| `/help`  | Quick how-to + main menu            |

---

## 3. Admin commands — full reference

These work **only** for Telegram user IDs listed in `ADMIN_IDS` (your `.env`).

### Viewing & navigating

| Command   | Example     | What it does                                       |
|-----------|-------------|----------------------------------------------------|
| `/admin`  | `/admin`    | Show this admin help text in the bot.              |
| `/stats`  | `/stats`    | Total users, orders, revenue, pending tickets.     |

### Managing products (this is the part you asked about)

> A *product* has: a unique `slug` (lowercase, no spaces), a display name, an
> emoji, a duration label (`12m`, `1m`, etc.), and a price in USDT.

| Action       | Command                                                       | Example                                                       |
|--------------|---------------------------------------------------------------|---------------------------------------------------------------|
| **List all** | `/products`                                                   | `/products`                                                   |
| **Add new**  | `/addproduct slug\|Name\|emoji\|duration\|price`              | `/addproduct chatgpt_pro_12m\|ChatGPT Pro\|🤖\|12m\|19.99`    |
| **Change price** | `/setprice slug NEW_PRICE`                                | `/setprice chatgpt_pro_12m 24.99`                             |
| **Hide / show**  | `/setactive slug on\|off`                                 | `/setactive cursor_pro_12m off` (hides from shop)             |
| **Edit description** | `/setdesc slug Multi-word description here`           | `/setdesc cursor_pro_12m Premium AI coding editor, 12-month` |
| **Set premium emoji** | `/setemoji slug ID`  (or `clear`)                    | `/setemoji cursor_pro_12m 5368324170671202286`                |
| **Add stock**| `/addstock slug` then send a `.txt` file (one credential / line) or paste lines | `/addstock cursor_pro_12m` then upload `cursor_keys.txt`     |
| **Show stock count** | `/stock slug`                                         | `/stock cursor_pro_12m`                                       |
| **Clear unsold stock** | `/clearstock slug confirm`                          | `/clearstock cursor_pro_12m confirm`                          |
| **Delete product** | `/delproduct slug confirm`                              | `/delproduct cursor_pro_12m confirm`                          |

> **Hide vs delete a product** — two options:
>
> 1. **Hide** with `/setactive slug off` — the product disappears from the
>    shop but its order history stays. Use this for products you want to
>    bring back later, or for any product that already has buyers.
> 2. **Hard delete** with `/delproduct slug confirm` — permanently removes
>    the product and any unsold stock. **Refused** if the product already
>    has order history (so historical sales never get orphaned).
>
> `/clearstock slug confirm` removes only the *unsold* stock items — sold
> ones stay so the buyer's order history is preserved.
>
> All of these have a corresponding button in the dashboard's *Products*
> page → click *Edit / Stock / Delete* for any row → *Danger zone*.

#### Stock pool — what you put in `.txt`

The bot delivers stock items as **plain text payloads** — usually one
account / key per line. Examples:

```
buyer1@gmail.com:Hunter2!
buyer2@gmail.com:Sw0rdfish
```

or license keys:

```
ABCD-EFGH-1234-5678
WXYZ-9876-LMNO-PQRS
```

Each `Buy now` pops one line atomically (no two users can buy the same line).
When the pool is empty the product shows **Out of stock** until you upload more.

### Managing deposits

| Command                              | What it does                                  |
|--------------------------------------|-----------------------------------------------|
| `/deposits`                          | List all pending deposit tickets.             |
| `/approve_dep ID [optional note]`    | Credit the user's wallet & notify them.       |
| `/reject_dep ID reason text here`    | Reject the ticket & notify the user.          |

When a user submits a deposit, every admin receives a Telegram message that
contains the exact `/approve_dep <id>` and `/reject_dep <id>` commands ready
to copy.

### Managing withdrawals

| Command                            | What it does                                                           |
|------------------------------------|------------------------------------------------------------------------|
| `/withdrawals`                     | List pending withdrawal requests.                                      |
| `/approve_wd ID [note]`            | Mark paid (the funds were already held). Send the user's USDT manually. |
| `/reject_wd ID reason`             | Reject & **automatically refund** the held amount to the user.         |

### Managing users

| Command                              | What it does                                              |
|--------------------------------------|-----------------------------------------------------------|
| `/whois USER_ID`                     | Show balance, join date, order count, ban status.         |
| `/credit USER_ID 10.00 [note]`       | Add 10 USDT to a user's wallet.                            |
| `/debit  USER_ID 5.00 [note]`        | Remove 5 USDT from a user's wallet.                       |
| `/ban USER_ID`                       | Block all bot interactions for that user.                 |
| `/unban USER_ID`                     | Unblock.                                                  |

### Broadcasting

| Command      | What it does                                                                                     |
|--------------|--------------------------------------------------------------------------------------------------|
| `/broadcast` | Then send the **next** message (text or photo with caption). It's forwarded to every active user. |

Use `/cancel` after `/broadcast` if you change your mind.

### Premium custom emojis

| Command                       | What it does                                                                                        |
|-------------------------------|-----------------------------------------------------------------------------------------------------|
| `/getemoji`                   | **Reply** to a message containing premium emojis to capture their `custom_emoji_id`.                |
| `/reload_emojis`              | Re-read `assets/premium_emojis.json` after you edit it (no restart needed).                         |
| `/setemoji slug ID`           | Bind a premium emoji to a specific product. Shown on the product detail screen.                     |
| `/setemoji slug clear`        | Drop the per-product premium binding (revert to the plain unicode glyph).                           |

To enable a UI premium emoji (Shop / Deposit / Profile / Refer / etc.):

1. From your Telegram Premium account, send a message with the premium emoji to your bot.
2. Reply to that message with `/getemoji`. The bot prints the IDs.
3. Open `assets/premium_emojis.json`, find the matching key (e.g. `"shop"`,
   `"wallet"`, `"refer"`, `"check"`, `"cross"`, `"warning"`, `"point_down"`,
   `"disabled"`, …) and set its `"id"` to the captured ID.
4. `/reload_emojis` — no restart needed.

To enable a premium emoji for a **specific product** (e.g. a custom Cursor mark
on the Cursor Pro detail page):

1. Capture the emoji ID with `/getemoji` (same as above).
2. Run `/setemoji cursor_pro_12m 5368324170671202286` (replace with your ID).
3. Open the product in the bot — premium subscribers now see your custom
   emoji; everyone else sees the unicode glyph from the `Emoji` field.

> **Important Telegram limitation — buttons can never show premium emojis.**
> The Telegram Bot API only supports `custom_emoji` entities **inside message
> bodies**, not inline-keyboard button labels. The 🛒 in the **Shop** button,
> the 💳 in **Deposit**, the 🔙 in **Back**, etc. will always render as the
> standard unicode glyph — that is a platform restriction, not a bot bug.
> Every place where a premium emoji *is* possible (every message your bot
> sends) is already wired through the registry.

Non-premium users see the unicode `fallback` instead — nothing breaks.

---

## 4. Web dashboard at a glance

URL: <http://127.0.0.1:8088>  · Password: the `DASHBOARD_PASSWORD` from `.env`.

| Page          | What you can do                                                          |
|---------------|--------------------------------------------------------------------------|
| **Dashboard** | Snapshot — users, orders, revenue, pending deposits / withdrawals, stock |
| **Products**  | Add a new product, edit any field, paste or upload `.txt` stock          |
| **Deposits**  | One-click Approve / Reject pending deposits                              |
| **Withdrawals** | One-click Approve / Reject withdrawal requests                          |
| **Orders**    | Recent fulfillment history with delivered payload (last 200 orders)      |
| **Users**     | Search by ID or username, ban / unban, credit / debit                    |

Everything you do here takes effect **instantly in the live bot** — both
processes share the same SQLite database file at `./data/bot.db`.

---

## 5. The referral economy

- Every user automatically gets a unique referral code on `/start`.
- Their referral link looks like `https://t.me/<your_bot>?start=ref_<code>`.
- When someone they referred makes a deposit, the referrer earns
  `REFERRAL_COMMISSION_PCT` (default **2 %**) of the deposit amount.
- When that referee makes any purchase, the referrer earns the same 2 %
  commission on the purchase price.
- On the referee's **first** purchase, the referrer additionally earns
  `REFERRAL_FIRST_PURCHASE_BONUS_USDT` (default **$0.50**).
- Referrers can transfer their available earnings to their main wallet
  from the *Refer & Earn* screen or the *Deposit* screen.

To change the rates, edit `.env`:

```
REFERRAL_COMMISSION_PCT=2.0
REFERRAL_FIRST_PURCHASE_BONUS_USDT=0.50
```

Then restart the bot.

---

## 6. Backup, reset, and data location

- **Database file**: `data/bot.db` (SQLite). Just copy it to back up.
- **Reset everything**: stop both processes, delete `data/bot.db`, start the
  bot again. It re-creates the schema and re-seeds the 21 starter products.
- **Premium emoji map**: `assets/premium_emojis.json`.
- **Logs**: printed to the terminal. Set `LOG_LEVEL=DEBUG` in `.env` for more.

---

## 7. Common questions

**Q. Can two users buy the same item?**
No. The buy flow uses a transactional pop — one row per buyer.

**Q. What if a user pays but never submits the proof?**
Nothing happens — no ticket is created. They will simply not have credit.
You can manually credit them with `/credit USER_ID amount`.

**Q. What if a user submits a fake screenshot?**
You see the screenshot in the admin notification. Reject with
`/reject_dep ID Fake screenshot — please send a real txn ID`. They get a
notification and can re-submit. Repeat offenders → `/ban USER_ID`.

**Q. How do I add a new payment method (PayPal, Stripe, etc.)?**
The current build supports manual Binance & UPI. Adding more methods
requires a small code change (extend `deposit_method_kb` in
`src/ui/keyboards.py` and add a branch in
`src/handlers/deposit.py:deposit_method`). Ask me when you're ready and
I'll add it.

**Q. Can I move from SQLite to Postgres?**
Yes — set `DATABASE_URL=postgresql+asyncpg://user:pass@host/db` in `.env`.
The schema is created automatically.

**Q. How do I run this 24/7?**
On a Windows server, set up Task Scheduler to run `python bot.py` (and
`python dashboard.py`) on startup. On Linux, systemd. Or use any process
manager (pm2, supervisord, NSSM on Windows). Just make sure both processes
are restarted after a crash.

---

## 8. Quick reference card

```
PUBLISH:
   1. Rotate BOT_TOKEN via @BotFather
   2. Set BINANCE_UID, UPI_ID in .env
   3. python bot.py
   4. (optional) python dashboard.py

ADD A PRODUCT:
   /addproduct chatgpt_pro_12m|ChatGPT Pro|🤖|12m|19.99
   /setdesc chatgpt_pro_12m Premium ChatGPT, 12-month subscription
   /addstock chatgpt_pro_12m
   (then upload a .txt with one account per line)

PAUSE / RESUME A PRODUCT:
   /setactive chatgpt_pro_12m off
   /setactive chatgpt_pro_12m on

CHANGE A PRICE:
   /setprice chatgpt_pro_12m 24.99

REMOVE STOCK / DELETE A PRODUCT:
   /clearstock chatgpt_pro_12m confirm   (delete unsold stock only)
   /delproduct chatgpt_pro_12m confirm   (delete product entirely — needs zero orders)
   /setactive  chatgpt_pro_12m off       (just hide it; safest if it already has buyers)

APPROVE A DEPOSIT:
   /deposits         (find the ID)
   /approve_dep 7

APPROVE A WITHDRAWAL:
   /withdrawals
   /approve_wd 3

CREDIT A USER MANUALLY:
   /credit 123456789 25.00 promo gift
```
