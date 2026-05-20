# Car Pricing & Negotiation Bot

A Telegram bot that estimates used-car prices and conducts a stateful price negotiation, powered by Claude.

## Architecture

A single Telegram chat carries the entire flow: the user posts a car description, the bot prices it and opens a negotiation, then both sides go back-and-forth in the same thread. The bot tracks an in-memory conversation state with three phases:

```
                ┌────────────────────────────────────────┐
                │ phase = idle                           │
                │   (no active negotiation)              │
                └──────────────────┬─────────────────────┘
                                   │  user posts a car description
                                   ▼
                          ┌─────────────────┐
                          │   Pricer (LLM)  │
                          └────────┬────────┘
                  insufficient_info│       │estimated
                                   │       │
                                   ▼       ▼
            ┌──────────────────────────┐  ┌─────────────────────────────┐
            │ phase = awaiting_info    │  │ phase = negotiating         │
            │ post clarifying question │  │ post opening message        │
            │ next user msg appends to │  │ seed history with opening   │
            │ description, re-run pricer  │                             │
            └────────────┬─────────────┘  └──────────────┬──────────────┘
                         │                               │  user replies
                         └───────────────────────────────┤
                                                         ▼
                                          ┌────────────────────────────┐
                                          │  Negotiator (LLM)          │
                                          │  - sees description        │
                                          │  - sees estimate range     │
                                          │  - sees full transcript    │
                                          │  - returns message + status│
                                          └─────────────┬──────────────┘
                                                        │
                                       status=negotiating│      status in
                                                        │   {deal_agreed,
                                                        │    walk_away}
                                                        ▼              ▼
                                                  (stay in)        reset → idle
                                                  negotiating
```

Conversation state lives in `conversation.py` as a module-level singleton. The negotiator agent receives the full running transcript on every turn, so the bot stays consistent on what it has offered and what it has in mind. The pricer's `high_price` is a hard ceiling — the bot never offers at or above it and will return `walk_away` rather than cross it.

When the negotiator returns `deal_agreed` or `walk_away`, the bot auto-resets to `idle` and the next user message starts a fresh car. There is no manual reset command.

The pricer, opening-message, and full description-to-estimate flow are persisted to SQLite (`car_requests`, `estimates`, `negotiations`). The multi-turn negotiation transcript itself lives in memory only — it is lost on restart.

## Setup

### 1. Create a Telegram bot

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to get your **bot token**.
3. Add the bot to your target group (so it can read and post messages).
4. Get the **chat ID** of the group — send a message in the group, then call:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   Look for `"chat": {"id": ...}` in the response. Group IDs are negative numbers.

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in all values:

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...                 # the chat the bot listens to and posts in
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-4-5
DATABASE_PATH=./bot.db
LOG_LEVEL=INFO
```

### 3. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run

```bash
python main.py
```

You should see:
```
[INFO] __main__: Database initialised at ./bot.db
[INFO] __main__: Bot starting — polling for messages in chat -123456789
```

## Usage

Everything happens in the configured chat. Post a car description and the bot will price it and open a negotiation. Reply to the bot's offers and it will counter, staying within its internal price range. When the bot judges the deal closed (agreed or stalled), it silently resets and the next message you post is treated as a brand-new car.

- **Detailed description** → opening negotiation message
  > _"2018 BMW 320d, 95k km, manual, second owner, full service history, asking €18k"_

- **Vague description** → clarifying question; bot stays in `awaiting_info` until it has enough to price
  > _"got a car for sale, interested?"_

## Known limitations

- State is in-memory only — restarting the bot loses any active negotiation.
- Only one negotiation at a time is supported. Multiple chats or multiple cars in parallel are not modelled.
