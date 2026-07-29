import json
import os
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

load_dotenv()


LOG_FILE = "run.jsonl"


class LogHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/run.jsonl"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"")
        else:
            self.send_error(404, "File Not Found")

    def log_message(self, format, *args):
        # Suppress noisy HTTP GET request logs in stdout
        pass


def start_log_web_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), LogHTTPRequestHandler)
    print(f"Log HTTP web server serving {LOG_FILE} on port {port}...")
    server.serve_forever()


# Start log web server in a daemon background thread
threading.Thread(target=start_log_web_server, daemon=True).start()



def read_required_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


TELEGRAM_BOT_TOKEN = read_required_env("TELEGRAM_BOT_TOKEN")

# Dynamic LOG_URL detection: uses LOG_URL env if provided, or auto-detects Render URL
LOG_URL = os.environ.get("LOG_URL")
if not LOG_URL or LOG_URL == "auto":
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        LOG_URL = f"{render_url.rstrip('/')}/run.jsonl"
    else:
        LOG_URL = "http://localhost:8000/run.jsonl"

# List of supported LLM Providers in priority order (as given in .env).
PROVIDERS = [
    {
        "name": "AI Pipe",
        "keys": ["AIPIPE_TOKEN"],
        "base_url": "https://aipipe.org/openai/v1",
        "default_model": "gpt-5-mini",
        "model_env": "AIPIPE_MODEL",
    },
    {
        "name": "Gemini API",
        "keys": ["GEMINI_API_KEY", "GEMINI_KEY"],
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-flash-latest",
        "model_env": "GEMINI_MODEL",
    },
    {
        "name": "Groq",
        "keys": ["GROQ_API_KEY"],
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "model_env": "GROQ_MODEL",
    },
    {
        "name": "NVIDIA NIM",
        "keys": ["NVIDIA_API_KEY", "NVIDIA_NIM_KEY", "NVIDIA_KEY"],
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "meta/llama-3.3-70b-instruct",
        "model_env": "NVIDIA_MODEL",
    },
    {
        "name": "OpenRouter",
        "keys": ["OPENROUTER_API_KEY", "OPENROUTER_KEY"],
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "model_env": "OPENROUTER_MODEL",
    },
]


def get_api_key_for_provider(provider: dict) -> str | None:
    for k in provider["keys"]:
        val = os.environ.get(k)
        if val:
            return val
    return None


active_providers = [p for p in PROVIDERS if get_api_key_for_provider(p)]
if not active_providers:
    keys_needed = ", ".join([p["keys"][0] for p in PROVIDERS])
    raise RuntimeError(
        f"Missing AI API key: please set at least one of ({keys_needed}) in environment."
    )


def get_llm_response(messages: list) -> str:
    errors = []

    for provider in PROVIDERS:
        api_key = get_api_key_for_provider(provider)
        if not api_key:
            continue

        model = (
            os.environ.get(provider["model_env"])
            or os.environ.get("MODEL")
            or provider["default_model"]
        )

        try:
            client = OpenAI(
                base_url=provider["base_url"],
                api_key=api_key,
            )
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            content = response.choices[0].message.content
            if content:
                return content
        except Exception as e:
            msg = f"{provider['name']} error ({model}): {e}"
            print(f"[Warning] {msg}")
            errors.append(msg)

    raise RuntimeError(f"Failed to get LLM response. Details:\n" + "\n".join(errors))


LOG_FILE = "run.jsonl"

# Keeps the last few messages per chat, so multi-turn questions work —
# "answer the LAST message" still needs the earlier ones for context.
conversation_history = {}
processed_update_ids = set()


def log_event(event: dict):
    event["timestamp"] = time.time()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")


def extract_json_object(reply_text: str) -> dict:
    try:
        return json.loads(reply_text)
    except json.JSONDecodeError:
        start, end = reply_text.find("{"), reply_text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise
        return json.loads(reply_text[start : end + 1])


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        update.effective_chat is None
        or update.message is None
        or update.message.text is None
    ):
        return

    # Deduplicate updates to avoid duplicate replies
    if update.update_id in processed_update_ids:
        return
    processed_update_ids.add(update.update_id)
    if len(processed_update_ids) > 1000:
        processed_update_ids.clear()

    chat_id = update.effective_chat.id
    user_text = update.message.text
    log_event({"type": "incoming", "chat_id": chat_id, "text": user_text})

    history = conversation_history.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_text})

    # Ask the AI to work out the answer. The system prompt tells it exactly how to
    # format the final reply — this is the part that MUST match what the question asked.
    system_prompt = (
        "You are a careful data analyst. The user's LAST message asks a data-analysis "
        "question and tells you exactly what JSON shape to reply with. Work out the "
        "real answer (use any public data you know, e.g. MOSPI statistics, general "
        "world knowledge, or arithmetic on numbers given in the message). "
        "Reply with ONLY that exact JSON object and absolutely nothing else — no "
        "explanation, no markdown, no code fences, just the raw JSON."
    )
    messages = [{"role": "system", "content": system_prompt}] + history[-6:]
    message_content = get_llm_response(messages)

    reply_text = message_content.strip()
    history.append({"role": "assistant", "content": reply_text})

    # Make sure we actually reply with valid JSON containing "log_url" — if the model
    # forgot the log_url field or wrapped it in markdown, fix it up here so the grader
    # never sees a malformed reply.
    parsed = extract_json_object(reply_text)
    parsed["log_url"] = LOG_URL
    final_reply = json.dumps(parsed)

    log_event({"type": "outgoing", "chat_id": chat_id, "text": final_reply})
    await update.message.reply_text(final_reply)


app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Bot is running... (Ctrl+C to stop)")
app.run_polling(drop_pending_updates=True)

