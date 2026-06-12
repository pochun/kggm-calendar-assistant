# KGGM Local Calendar Assistant

Local web assistant for querying Google Calendar and turning natural language into events.

It uses:

- Ollama on `127.0.0.1:11434`
- Local model `gemma4-agent-12b`
- Google Calendar OAuth
- No paid AI API tokens

It supports:

- multi-turn event completion
- existing event lookup
- event preview before creation

## Start

Open Ollama first:

```bash
open -a Ollama
```

Run the app:

```bash
git clone https://github.com/pochun/kggm-calendar-assistant.git
cd kggm-calendar-assistant
python3 assistant_app.py
```

Open:

```text
http://127.0.0.1:8787
```

## Google Calendar Setup

Create a Google Cloud OAuth client:

1. Go to Google Cloud Console.
2. Enable Google Calendar API.
3. Create an OAuth client ID for a web application.
4. Add this authorized redirect URI:

```text
http://127.0.0.1:8787/oauth2callback
```

Start the app with credentials:

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
python3 assistant_app.py
```

Then click `Connect Google Calendar` in the web UI.

If you previously connected an older version of the app, reconnect once so Google grants the read scope needed for calendar lookup.

OAuth tokens are stored outside this repo:

```text
~/.kggm-assistant/google-token.json
```

## Safety Notes

- Events are not created immediately.
- The app first shows an event preview.
- You must click `Create Event` before it writes to Google Calendar.
- The app asks for Google Calendar event read/create permissions:
  - `https://www.googleapis.com/auth/calendar.events`
  - `https://www.googleapis.com/auth/calendar.readonly`
- It does not use OpenAI, OpenRouter, Anthropic, or other paid AI APIs.

## Example Prompts

```text
明天上午我有什麼行程？
```

```text
幫我加一個牙醫
```

Then answer the follow-up:

```text
明天下午三點，在台大醫院，一小時
```

## Optional Settings

```bash
export OLLAMA_MODEL="gemma4-agent-12b"
export OLLAMA_URL="http://127.0.0.1:11434"
export KGGM_PORT="8787"
export KGGM_TIMEZONE="Asia/Taipei"
export GOOGLE_CALENDAR_ID="primary"
```
