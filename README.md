# LINE OA Messages (POC)

ระบบตัวอย่าง (Proof of Concept) สำหรับ **รับข้อความจาก LINE Official Account** ผ่าน Webhook,
บันทึกลงฐานข้อมูล **SQLite**, และแสดงข้อความทั้งหมดเป็น **ตาราง (table) บนหน้าเว็บแบบเรียลไทม์**
พร้อมความสามารถในการ **ตอบกลับ (reply)** และ **ส่งข้อความหาผู้ใช้ (push)**

> 📌 โปรเจกต์นี้สร้างจากเทมเพลต [`lumduan/python-template`](https://github.com/lumduan/python-template)
> (uv · src layout · ruff · mypy strict · pytest · Docker · GitHub Actions)

---

## ✨ ความสามารถหลัก (Features)

- 📥 **รับ Webhook จาก LINE** — ปลายทาง FastAPI ที่ `POST /line/webhook`
- 🔐 **ตรวจสอบลายเซ็น** `X-Line-Signature` (HMAC-SHA256 จาก raw body) ตามมาตรฐานของ LINE
- 🗄️ **บันทึกข้อมูลลง SQLite** — เก็บผู้ใช้ (users), เหตุการณ์ดิบ (events), ข้อความ (messages) และการตอบกลับ (replies)
- 📊 **แดชบอร์ดเรียลไทม์** — ตารางข้อความสร้างด้วย **NiceGUI** รีเฟรชอัตโนมัติทุก 2 วินาที
- 🤖 **ตอบกลับอัตโนมัติ (echo)** ทุกข้อความ และมีปุ่ม **Push** ส่งข้อความหา user id ได้จากหน้าเว็บ
- 🐳 **รันใน Container เดียว** เปิด 2 พอร์ต (webhook + dashboard)
- 🔒 **เก็บความลับไว้ใน `.env` เท่านั้น** (repo นี้เป็น public — มีแต่ `.env.example` ที่ถูก commit)

## 🧱 สถาปัตยกรรม (Architecture)

```
        LINE Platform
             │  (POST + X-Line-Signature)
             ▼
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  Webhook (FastAPI)  :9990    │        │   Dashboard (NiceGUI)  :9991  │
│  /line/webhook               │        │   ตารางข้อความ + ปุ่ม Push      │
│  - ตรวจลายเซ็น               │        │   - refresh ทุก 2 วินาที        │
│  - บันทึกข้อมูล              │        └───────────────┬──────────────┘
│  - ตอบกลับ (echo)            │                        │
└──────────────┬──────────────┘                        │
               └──────────────┬─────────────────────────┘
                              ▼
                       SQLite  (./data/line.db)
```

ทั้งสองพอร์ตรันใน **โปรเซสเดียว / คอนเทนเนอร์เดียว** (uvicorn 2 ตัวผ่าน `asyncio.gather` ใน `src/main.py`)

| พอร์ต | บริการ | รายละเอียด |
|------|--------|-----------|
| **9990** | Webhook (FastAPI) | นำ URL นี้ไปตั้งค่าใน LINE Developers Console |
| **9991** | Dashboard (NiceGUI) | เปิดดูข้อความในเบราว์เซอร์ |

## 🛠️ เทคโนโลยีที่ใช้ (Tech stack)

FastAPI · NiceGUI · SQLAlchemy 2.0 · SQLite · line-bot-sdk v3 · pydantic-settings · uv · Python 3.12

---

## 🚀 เริ่มต้นใช้งาน (Getting started)

### 1) เตรียมความลับใน `.env`

คัดลอกไฟล์ตัวอย่างแล้วใส่ค่าจริงจาก **LINE Developers Console**:

```bash
cp .env.example .env
```

แก้ไขค่าต่อไปนี้ในไฟล์ `.env` (ห้าม commit ไฟล์นี้):

```dotenv
LINE_CHANNEL_SECRET=<channel secret ของคุณ>
LINE_CHANNEL_ACCESS_TOKEN=<channel access token ของคุณ>
```

> ⚠️ **ข้อควรระวังด้านความปลอดภัย:** repo นี้เป็น public — `.env`, `data/`, และ `*.db`
> ถูกใส่ไว้ใน `.gitignore` แล้ว ห้ามนำ token/secret ขึ้น GitHub โดยเด็ดขาด

### 2) รันแบบโลคอลด้วย uv

```bash
uv sync --all-groups          # ติดตั้ง dependencies
uv run python -m src.main     # รัน webhook (:9990) + dashboard (:9991)
```

เปิดแดชบอร์ดที่ <http://localhost:9991>

### 3) รันด้วย Docker

```bash
docker compose up --build
```

- Webhook: <http://localhost:9990/line/webhook>
- Dashboard: <http://localhost:9991>
- ฐานข้อมูลถูกเก็บไว้ที่โฟลเดอร์ `./data` (ผ่าน volume) จึงไม่หายเมื่อ restart

---

## 🔗 เชื่อมต่อกับ LINE จริง

LINE ต้องการ URL แบบ **HTTPS สาธารณะ** จึงต้องเปิด tunnel มาที่พอร์ต webhook (9990):

```bash
cloudflared tunnel --url http://localhost:9990
# หรือ
ngrok http 9990
```

จากนั้นนำ URL ไปตั้งใน LINE Developers Console:

```
Webhook URL:  https://<โดเมน-tunnel>/line/webhook
```

แล้วกด **Verify** และเปิด **Use webhook** ให้เรียบร้อย

## 🧪 ทดสอบโดยไม่ต้องต่อ LINE

มีสคริปต์สำหรับยิง webhook ปลอม (ลงลายเซ็นถูกต้องด้วย channel secret ของคุณ):

```bash
# เทอร์มินัล 1 — รันแบบ offline (ปิดการตอบกลับ เพราะ reply token เป็นของปลอม)
AUTO_REPLY=false uv run python -m src.main

# เทอร์มินัล 2
uv run python scripts/send_test_webhook.py "สวัสดีครับ"
```

ข้อความจะปรากฏในตารางแดชบอร์ดภายใน ~2 วินาที

---

## ✅ การพัฒนาและตรวจคุณภาพโค้ด (Quality gate)

```bash
uv run ruff check .            # lint
uv run ruff format --check .   # ตรวจ format
uv run mypy src tests          # ตรวจ type (strict)
uv run pytest                  # ทดสอบ + coverage (ต้อง ≥ 80%)
```

## 📁 โครงสร้างโปรเจกต์ (Project structure)

```
src/
  main.py            # entrypoint: uvicorn 2 ตัว (webhook :9990, dashboard :9991)
  config.py          # โหลดค่าจาก .env (pydantic-settings)
  db.py              # engine, session, init_db()
  models.py          # ORM: LineUser, Event, Message, Reply
  services.py        # ตรรกะบันทึกข้อมูล (get_or_create_user, persist_inbound_event, ...)
  line/
    webhook.py       # ตรวจลายเซ็น + parse + บันทึก + ตอบกลับ
    client.py        # reply / push / get_profile (line-bot-sdk)
  dashboard/
    app.py           # FastAPI + NiceGUI (ui.run_with)
    pages.py         # ตารางข้อความ + ฟอร์ม push
scripts/
  send_test_webhook.py   # ยิง webhook ตัวอย่างที่ลงลายเซ็นแล้ว
tests/                   # signature / persist / services / client
```

## 🗃️ ฐานข้อมูล (Database)

| ตาราง | เก็บอะไร |
|-------|---------|
| `users` | ผู้ใช้ LINE (เติมชื่อ/รูปจาก Profile API เมื่อพบครั้งแรก) |
| `events` | เหตุการณ์ webhook ดิบทั้งหมด (เก็บ JSON ไว้ตรวจสอบ) |
| `messages` | ข้อความขาเข้าจาก message event |
| `replies` | ข้อความขาออกที่เราส่ง (reply / push) |

## 📄 License

[MIT](LICENSE)
