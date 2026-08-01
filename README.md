# 🤖 TDS Data Analyst Telegram Bot

An automated, resilient Data Analyst Telegram Bot built for the **IITM BS Tools in Data Science (TDS)** project evaluation.

The bot receives natural language data-analysis queries via Telegram, computes precise analytical answers, synthesizes structured JSON payloads using multi-provider LLM failover, logs events to `run.jsonl`, and dynamically serves logs over HTTP/HTTPS.

---

## 🌟 Key Features

- **Multi-Provider LLM Failover Matrix**: Priority-ordered cascade across 5 major AI providers (`AI Pipe` → `Groq` → `Gemini API` → `OpenRouter` → `NVIDIA NIM`). If a provider encounters rate limits (429), timeouts, or model errors, the bot seamlessly falls back to the next available provider.
- **Embedded Log Web Server**: Features an integrated daemon HTTP server that live-serves `run.jsonl` at `/run.jsonl`, `/`, `/ping`, and `/health` endpoints for grading and health monitoring.
- **Auto-Detecting Log URL**: Automatically resolves the public `LOG_URL` using Render environment variables (`RENDER_EXTERNAL_URL`) or local configuration.
- **Strict JSON Enforcement & Repair**: Parses model outputs and extracts valid JSON payloads, guaranteeing the required `"answer"` and `"log_url"` fields are delivered back to Telegram.
- **Keep-Alive Self-Pinger**: Built-in background pinger prevents free-tier cloud hosting (e.g. Render) from spinning down due to inactivity.
- **Update Deduplication & Multi-Turn History**: Deduplicates Telegram updates to prevent duplicate replies and maintains concise conversation history for contextual follow-ups.

---

## ⚡ Supported LLM Providers & Models

The bot automatically activates any provider for which an API key is present in `.env`. Providers are queried in the following priority order:

| Priority | Provider | Default Model | Key Env Variable | Strengths & Capabilities |
| :---: | :--- | :--- | :--- | :--- |
| **#1** | **Groq** | `llama-3.3-70b-versatile` | `GROQ_API_KEY` | **Ultra-Fast Speed**: ~300+ tokens/sec LPU hardware with 70B parameter model reasoning. |
| **#2** | **Gemini API** | `gemini-flash-latest` | `GEMINI_API_KEY` | **Google Gemini**: Massive context window, strong math and structured data skills. |
| **#3** | **AI Pipe** | `gpt-4o-mini` | `AIPIPE_TOKEN` | **Flagship Intelligence**: Top-tier data analysis, math precision, and strict JSON adherence. |
| **#4** | **OpenRouter** | `meta-llama/llama-3.3-70b-instruct` | `OPENROUTER_API_KEY` | **Multi-Node Fallback**: Reliable 70B model fallback routed across OpenRouter's cloud network. |
| **#5** | **NVIDIA NIM** | `nvidia/nemotron-mini-4b-instruct` | `NVIDIA_API_KEY` | **Lightweight Backup**: Fast 4B parameter native NVIDIA model as a final safety net. |

> 💡 **Custom Model Overrides**: You can override any default model without changing code by setting custom environment variables in `.env` (e.g., `AIPIPE_MODEL=gpt-5`, `GROQ_MODEL=llama-3.3-70b-versatile`, `GEMINI_MODEL=gemini-2.0-flash`, etc.).

---

## 📁 Repository Structure

```text
tds-data-analyst-bot/
├── bot.py             # Main Telegram bot logic, LLM failover, & embedded HTTP log server
├── requirements.txt   # Python package dependencies
├── .env.example       # Environment variables template
├── .env               # Secrets & API keys configuration (git-ignored)
├── README.md          # Project documentation
└── run.jsonl          # Event log file generated automatically at runtime
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.10+**
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 2. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/tds-data-analyst-bot.git
cd tds-data-analyst-bot
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and insert your credentials:

```bash
cp .env.example .env
```

Example `.env` configuration:
```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
LOG_URL=auto

# AI Credentials (Provide at least one)
AIPIPE_TOKEN=your_aipipe_token
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
NVIDIA_API_KEY=your_nvidia_api_key
```

---

## 💻 Running the Bot Locally

```bash
python bot.py
```

Upon launch:
1. The Telegram Bot starts polling for incoming user messages.
2. The embedded log web server starts listening on port `8000` (or `PORT` env) to serve `run.jsonl` at `http://localhost:8000/run.jsonl`.

---

## 🌐 Cloud Deployment (e.g. Render / Koyeb)

1. Push this repository to GitHub.
2. Create a new **Web Service** on [Render](https://render.com/).
3. Configure build & start settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
4. Add environment variables under **Environment** in the Render Dashboard:
   - Set `TELEGRAM_BOT_TOKEN` and at least one LLM API key (`AIPIPE_TOKEN`, `GROQ_API_KEY`, etc.).
   - Set `LOG_URL=auto` (the bot will auto-detect your Render URL and serve logs at `https://<your-app>.onrender.com/run.jsonl`).
5. Click **Deploy Web Service**.

---

## ⏱️ Preventing Render Free Tier Spindown (24/7 Uptime)

Render free tier instances go to sleep after **15 minutes of inactivity**. Use either of the following methods to keep your bot awake:

### Option 1: Built-in Keep-Alive Pinger (Automatic)
The bot includes a built-in background thread that automatically pings itself every 10 minutes when running on Render.
- If `RENDER_EXTERNAL_URL` or `PING_URL` is set in the environment, the pinger automatically triggers every 600 seconds (`PING_INTERVAL`).

### Option 2: External Health Monitor (UptimeRobot)
1. Register a free account at [UptimeRobot](https://uptimerobot.com/).
2. Add a new monitor:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `TDS Data Analyst Bot`
   - **URL**: `https://<your-render-app>.onrender.com/ping`
   - **Interval**: `5 minutes` or `10 minutes`

---

## 🩺 Available Health & Log Endpoints

| Endpoint | HTTP Method | Description |
| :--- | :---: | :--- |
| `/run.jsonl` or `/` | `GET` | Returns live JSONL logs containing incoming/outgoing events. |
| `/ping` or `/health` | `GET` / `HEAD` | Returns `{"status":"ok","message":"pong"}` (HTTP 200). |

---

## 📜 License

Distributed under the MIT License for academic and evaluation purposes in the IITM BS Tools in Data Science (TDS) course.
