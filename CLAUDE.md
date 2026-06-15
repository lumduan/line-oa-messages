# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this is

A **proof-of-concept** that:

1. Receives **LINE Official Account** webhook events via a **FastAPI** endpoint.
2. **Verifies** the `X-Line-Signature` header (HMAC-SHA256 over the *raw* body).
3. Persists **users, raw events, messages, and replies** to **SQLite**.
4. Shows the stored messages on a **live, auto-refreshing NiceGUI dashboard**.
5. Can **reply** (auto-echo) and **push** messages back to LINE.

Built from the `lumduan/python-template` conventions (uv, src/ layout, ruff, mypy-strict,
pytest ≥80% coverage, multi-stage Docker, GitHub Actions).

> The customer for this system is Thai — **`README.md` is written primarily in Thai (ภาษาไทย)**.
> This file (`CLAUDE.md`) and code comments stay in English.

## Ports

| Port | Service | Notes |
|------|---------|-------|
| **9990** | LINE webhook (FastAPI) | `POST /line/webhook` — set this URL in the LINE console |
| **9991** | Dashboard (NiceGUI)    | `GET /` — live message table + push form |

Both run in **one container / one process** (two `uvicorn` servers via `asyncio.gather` in `src/main.py`).

## Stack

- **FastAPI** — webhook API.
- **NiceGUI** (built on FastAPI) — dashboard; `ui.table` + `ui.timer` live refresh.
- **SQLAlchemy 2.0** typed declarative models on **SQLite** (no mypy plugin needed).
- **line-bot-sdk v3** — signature verification/parsing (`linebot.v3.webhook.WebhookParser`)
  and sending (`linebot.v3.messaging`).
- **pydantic-settings** — config loaded from `.env`.
- Python **3.12** at runtime (Docker); `requires-python = ">=3.11"`, CI tests 3.11 + 3.12.

## Layout

```
src/
  main.py            # entrypoint: two uvicorn servers (webhook :9990, dashboard :9991)
  config.py          # pydantic-settings Settings (loads .env)
  db.py              # engine, SessionLocal, Base, init_db(), session_scope()
  models.py          # LineUser, Event, Message, Reply (typed Mapped[...])
  services.py        # get_or_create_user, persist_inbound_event, record_reply, list_messages
  line/
    webhook.py       # build_webhook_app(): router /line/webhook — verify, parse, persist, echo
    client.py        # reply_text / push_text / get_profile (line-bot-sdk wrappers)
  dashboard/
    app.py           # build_dashboard_app(): FastAPI + ui.run_with(app)
    pages.py         # @ui.page("/"): live table + push form
scripts/
  send_test_webhook.py   # POST a sample event with a correctly-computed signature
tests/                   # signature / persist / services / client  (≥80% coverage)
data/                    # SQLite file lives here (git-ignored, Docker volume)
```

## Commands

```bash
uv sync --all-groups                 # install deps (incl. dev)
uv run python -m src.main            # run app -> :9990 webhook, :9991 dashboard
uv run python scripts/send_test_webhook.py   # POST a signed sample event (use AUTO_REPLY=false)

uv run ruff check .                  # lint
uv run ruff format --check .         # format check
uv run mypy src tests                # type check (strict)
uv run pytest                        # tests + coverage (fails under 80%)

docker compose up --build            # run in a container (both ports + ./data volume)
```

## Conventions

- `src/` layout; run as `python -m src.main`.
- **mypy strict** (`ignore_missing_imports = true` covers untyped `linebot`/`nicegui`).
- **ruff** line length 100; rules `E, F, I, UP, B, SIM`.
- **pytest** ≥80% coverage; `src.line.client` (the only network surface) is mocked in tests.
- **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:` …); update `CHANGELOG.md`.

## LINE Messaging API notes

- **Signature**: `base64(HMAC-SHA256(channel_secret, raw_request_body))` must equal `X-Line-Signature`.
  Verify against the **raw bytes** (`await request.body()`), never re-serialized JSON.
- **Reply API**: `POST https://api.line.me/v2/bot/message/reply`, `Authorization: Bearer <token>`,
  body `{ replyToken, messages[] }`. Reply token is **one-time** and valid **~3 minutes**; ≤5 messages.
- **Push API**: `POST .../v2/bot/message/push`, body `{ to: <userId>, messages[] }`.
- **Profile**: `GET .../v2/bot/profile/{userId}` → `displayName`, `pictureUrl`, `statusMessage`.
- **Channel secret** verifies signatures; **channel access token** authorizes API calls.

## Secrets & security (repo is PUBLIC)

- **All secrets live ONLY in `.env`** (git-ignored). `.env.example` holds placeholders and IS committed.
- Never commit `.env`, `data/`, or `*.db` (all in `.gitignore`).
- `LINE_CHANNEL_SECRET` and `LINE_CHANNEL_ACCESS_TOKEN` come from the LINE Developers Console.
- Set `AUTO_REPLY=false` for offline/local testing so a fake reply token doesn't call LINE.

## Exposing to real LINE

LINE needs a public HTTPS URL. Run a tunnel to the webhook port and register it:

```bash
cloudflared tunnel --url http://localhost:9990    # or: ngrok http 9990
# Webhook URL in LINE console -> https://<tunnel-host>/line/webhook  (then click Verify)
```
