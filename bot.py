import json
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse


def load_env_file():
    """Load .env if present; hosting environment variables take precedence."""
    path = ".env"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

if not BOT_TOKEN or not GEMINI_KEY:
    raise RuntimeError("BOT_TOKEN aur GEMINI_API_KEY environment variables set karo.")

TG = f"https://api.telegram.org/bot{BOT_TOKEN}"
AI = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
histories = {}


def api(url, data=None, headers=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers or {})

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
            print(f"Server busy. Retry {attempt + 1}/3...")
            time.sleep(2 ** attempt)
        except urllib.error.URLError as exc:
            if attempt == 2:
                raise
            print(f"Connection issue. Retry {attempt + 1}/3: {exc}")
            time.sleep(2 ** attempt)


def send(chat_id, msg):
    api(
        TG + "/sendMessage",
        {"chat_id": chat_id, "text": str(msg)[:4000]},
        {"Content-Type": "application/json"},
    )


def ask(uid, message):
    history = histories.setdefault(uid, [])
    history.append({"role": "user", "parts": [{"text": message}]})
    history[:] = history[-6:]

    result = api(
        AI,
        {
            "systemInstruction": {
                "parts": [{"text": "You are Aastha, a helpful AI assistant. Reply naturally in Hindi, Hinglish or English."}]
            },
            "contents": history,
            "generationConfig": {"maxOutputTokens": 300},
        },
        {"Content-Type": "application/json", "x-goog-api-key": GEMINI_KEY},
    )

    candidates = result.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini ne koi response nahi diya: " + json.dumps(result)[:1000])
    parts = candidates[0].get("content", {}).get("parts", [])
    answer = "\n".join(p.get("text", "") for p in parts if p.get("text"))
    if not answer:
        raise RuntimeError("Gemini response khaali tha.")

    history.append({"role": "model", "parts": [{"text": answer}]})
    history[:] = history[-8:]
    return answer


def main():
    print("Aastha Messenger Bot starting...")
    info = api(TG + "/getMe")
    if not info.get("ok"):
        raise RuntimeError("Telegram token verify nahi hua: " + str(info))
    bot_id = info["result"]["id"]
    print("Telegram connected:", info["result"].get("username"))

    api(TG + "/deleteWebhook", {"drop_pending_updates": True}, {"Content-Type": "application/json"})
    offset = None
    print("BOT IS ONLINE!")

    while True:
        try:
            url = TG + "/getUpdates?timeout=30"
            if offset is not None:
                url += "&offset=" + str(offset)
            result = api(url)

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg or not msg.get("text") or not msg.get("from"):
                    continue

                chat_id = msg["chat"]["id"]
                uid = f"{chat_id}:{msg['from']['id']}"
                message = msg["text"].strip()
                chat_type = msg["chat"].get("type")

                if chat_type in ("group", "supergroup"):
                    reply = msg.get("reply_to_message") or {}
                    reply_from = reply.get("from") or {}
                    is_bot_reply = reply_from.get("id") == bot_id
                    has_wake_word = bool(re.search(r"(?i)(?<!\w)aastha(?!\w)", message))
                    is_greeting = bool(re.fullmatch(r"(?i)(hi|hello|hey|hii|namaste)[\s!?.😊🙏]*", message))
                    if not (is_bot_reply or has_wake_word or is_greeting):
                        continue
                    if has_wake_word:
                        message = re.sub(r"(?i)(?<!\w)aastha(?!\w)", "", message).strip(" \t\r\n,.:;!?-")
                    if has_wake_word and not message:
                        send(chat_id, "Haan ji! 😊 Boliye, kya hua?")
                        continue

                if message.startswith("/start"):
                    send(chat_id, "Welcome to Aastha Messenger Bot! 🤖\nMujhse kuch bhi poochho.")
                elif message.startswith("/reset"):
                    histories.pop(uid, None)
                    send(chat_id, "New conversation started! ✅")
                elif message.startswith("/help"):
                    send(chat_id, "/start - Start\n/reset - New chat\n/help - Help")
                else:
                    try:
                        send(chat_id, ask(uid, message))
                    except Exception as exc:
                        print("AI ERROR:", exc)
                        send(chat_id, "AI error aaya. Thodi der baad try karo.")

        except Exception as exc:
            print("TELEGRAM ERROR:", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
