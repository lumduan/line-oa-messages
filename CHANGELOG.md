# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- FastAPI **LINE webhook** at `POST /line/webhook` (port 9990) with `X-Line-Signature`
  HMAC-SHA256 verification over the raw request body (via `line-bot-sdk` v3).
  Also accepted at the root path `POST /` (the webhook runs on its own subdomain).
- **NiceGUI dashboard** (port 9991) with a live, auto-refreshing message table and a
  push-message form; both servers run in one process via `asyncio.gather`.
- **SQLite persistence** with SQLAlchemy 2.0 typed models: `LineUser`, `Event`,
  `Message`, `Reply`.
- Outbound **LINE client** wrappers: `reply_text`, `push_text`, `get_profile`.
- Auto-echo replies to inbound text messages (toggle with `AUTO_REPLY`).
- Best-effort user profile enrichment on first contact.
- `scripts/send_test_webhook.py` to post a correctly-signed sample event locally.
- Multi-stage `Dockerfile` (Python 3.12) and `docker-compose.yml` exposing both ports
  with a `./data` volume for the SQLite file.
- Test suite (signature, persistence, services, client) with ≥80% coverage.
- Thai-language `README.md`; English `CLAUDE.md` for contributor/agent guidance.

### Changed
- Rewrote `README.md` for non-developer readers: leads with the conversation-history
  feature and a sample message table (real `text`/`image`/`sticker`/`file` types), and
  folds Docker/setup/dev details into a collapsible section at the bottom.

[Unreleased]: https://github.com/lumduan/line-oa-messages/commits/main
