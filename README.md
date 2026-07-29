# TDS Data Analyst Telegram Bot

An automated Data Analyst Telegram Bot built for the IITM BS Tools in Data Science (TDS) project evaluation. The bot processes data-analysis queries, synthesizes structured JSON answers using multi-provider LLM failover, logs incoming/outgoing events, and serves `run.jsonl` dynamically over HTTP/HTTPS.

## Key Features

- **Multi-Provider LLM Fallback**: Automatically tries active LLM providers in priority order (`AI Pipe` → `Gemini API` → `Groq` → `NVIDIA NIM` → `OpenRouter`). If a provider hits rate limits or error codes (e.g. 429), it falls back seamlessly to the next configured provider.
- **Embedded Log Web Server**: Features an integrated daemon HTTP server that serves `run.jsonl` live at `/run.jsonl` for evaluation graders when deployed to cloud hosts (Render, Koyeb, VPS).
- **Strict JSON Enforcement**: Parses and validates model responses to guarantee strict, raw JSON payloads containing the required `log_url` field.
- **Update Deduplication**: Prevents duplicate message handling and bot conflict errors.

## Project Structure

```text
.
├── bot.py             # Main Telegram bot & embedded HTTP log server
├── requirements.txt   # Dependencies
├── .env.example       # Environment variables template
├── .env               # Local environment secrets (ignored by git)
└── run.jsonl          # Event log file (generated at runtime)
```

## Setup & Installation

### 1. Prerequisites
- Python 3.10+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 2. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/tds-data-analyst-bot.git
cd tds-data-analyst-bot
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Example `.env` configuration:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyZ
LOG_URL=https://your-app-name.onrender.com/run.jsonl

# LLM Provider Keys (Provide at least one)
AIPIPE_TOKEN=your_aipipe_token
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
NVIDIA_API_KEY=your_nvidia_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Running the Bot Locally

```bash
python bot.py
```

Upon startup, the bot will start polling for Telegram messages and listening on HTTP port `8000` (or the configured `PORT`) to serve `run.jsonl`.

## Deployment (e.g., Render / Koyeb)

1. Push this repository to GitHub.
2. Create a **New Web Service** on [Render](https://render.com/).
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `python bot.py`
5. Add your environment variables in the Render dashboard. Set `LOG_URL` to `https://<your-render-app>.onrender.com/run.jsonl`.
6. Deploy! The bot and live `run.jsonl` HTTP endpoint will be online.

---

## Keeping Render Awake (Preventing Inactivity Spindown)

Render's free tier Web Services spin down (go to sleep) after **15 minutes of inactivity**. When slept, incoming Telegram messages or log evaluation requests will experience latency while the app cold-starts.

To keep your bot active **24/7**, use any of the following pinging solutions:

### Option 1: External Pinger (UptimeRobot - Recommended)

1. Sign up for a free account at [UptimeRobot.com](https://uptimerobot.com/).
2. Click **+ Add New Monitor**.
3. Configure the monitor details:
   - **Monitor Type**: `HTTP(s)` or `Keyword`
   - **Friendly Name**: `TDS Data Analyst Bot`
   - **URL (or IP)**: `https://<your-app-name>.onrender.com/ping` (or `/health`)
   - **Monitoring Interval**: `5 minutes` or `10 minutes`
4. Click **Create Monitor**. UptimeRobot will ping your server every few minutes, preventing Render from going idle.

### Option 2: Built-in Self-Pinger

`bot.py` includes a built-in keep-alive background thread that periodically pings its own endpoint:

1. In your Render Dashboard, add an environment variable:
   - `RENDER_EXTERNAL_URL` = `https://<your-app-name>.onrender.com` (Render sets this automatically if enabled, or set `PING_URL=https://<your-app-name>.onrender.com`)
   - `PING_INTERVAL` = `600` (optional, default 10 minutes)
2. On startup, `bot.py` will launch a background thread that sends an HTTP GET request to `https://<your-app-name>.onrender.com/ping` every 10 minutes.

### Available Health & Ping Endpoints

- `GET /ping` or `GET /health` or `GET /healthz` — Returns `{"status":"ok","message":"pong"}`
- `HEAD /ping` or `HEAD /` — Returns `200 OK` (lightweight for HEAD pingers)

