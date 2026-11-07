# Aastha Messenger Bot

A Telegram AI chat bot powered by the Gemini API. This package is configured as a background worker and uses Telegram long polling.

## Files
- `bot.py` — bot source code
- `requirements.txt` — dependencies (Python standard library only)
- `.env.example` — environment-variable template; copy to `.env` for local use
- `Procfile` — worker start command for compatible hosts
- `runtime.txt` — Python runtime hint for hosts that support it

## Configure
Set these environment variables in your hosting dashboard:

- `BOT_TOKEN` — Telegram bot token from BotFather
- `GEMINI_API_KEY` — Gemini API key
- `GEMINI_MODEL` — optional; defaults to `gemini-3.1-flash-lite`

Do not upload your real `.env` file or share your API keys publicly. If a token/key has been exposed, revoke or regenerate it.

## Start

```bash
python bot.py
```

The host must support a continuously running background worker. Free hosting plans may sleep, stop workers, or impose usage limits, so 24/7 uptime is not guaranteed by this ZIP alone.

## Notes
- This bot uses Telegram long polling. Do not run two copies with the same bot token at the same time.
- Group replies are triggered by replying to the bot, mentioning `Aastha`, or sending a greeting.
- Conversation history is kept in memory and is cleared if the process restarts.
