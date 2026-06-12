#!/usr/bin/env python3
import base64
import datetime as dt
import html
import json
import os
import re
import secrets
import socket
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


APP_HOST = os.environ.get("KGGM_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("KGGM_PORT", "8787"))
APP_ORIGIN = f"http://{APP_HOST}:{APP_PORT}"
MODEL = os.environ.get("OLLAMA_MODEL", "gemma4-agent-12b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
TIMEZONE = os.environ.get("KGGM_TIMEZONE", "Asia/Taipei")
STATE_DIR = Path.home() / ".kggm-assistant"
TOKEN_FILE = STATE_DIR / "google-token.json"
OAUTH_STATE_FILE = STATE_DIR / "oauth-state.txt"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]
REQUIRED_QUERY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
SESSION = {
    "messages": [],
    "pending_event": None,
}


INDEX_HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>KGGM Local Calendar Assistant</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f7f8fa;
      --surface: #ffffff;
      --text: #18202a;
      --muted: #667085;
      --line: #d8dee8;
      --accent: #166c5f;
      --accent-2: #2f5ea8;
      --danger: #a83232;
      --shadow: 0 8px 24px rgba(17, 24, 39, .08);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #111418;
        --surface: #191f27;
        --text: #edf1f7;
        --muted: #aab2c0;
        --line: #303946;
        --accent: #5fb7a6;
        --accent-2: #8fb5f1;
        --danger: #ff8787;
        --shadow: none;
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      min-height: 100vh;
    }
    aside {
      border-right: 1px solid var(--line);
      padding: 24px;
      background: color-mix(in srgb, var(--surface) 84%, var(--bg));
    }
    section {
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-width: 0;
      min-height: 100vh;
    }
    header {
      padding: 22px 28px;
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 14px;
      color: var(--muted);
      font-weight: 650;
    }
    p { margin: 0 0 12px; }
    .muted { color: var(--muted); }
    .status {
      display: grid;
      gap: 10px;
      margin: 18px 0 24px;
    }
    .pill {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
    }
    .pill b { font-weight: 650; }
    .ok { color: var(--accent); }
    .bad { color: var(--danger); }
    .btn {
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      color: var(--text);
      padding: 10px 14px;
      font-weight: 650;
      cursor: pointer;
      min-height: 42px;
    }
    .btn.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }
    .btn:disabled {
      opacity: .55;
      cursor: wait;
    }
    .chat {
      padding: 24px 28px;
      overflow: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .msg {
      max-width: 820px;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
      white-space: pre-wrap;
    }
    .msg.user {
      align-self: flex-end;
      background: color-mix(in srgb, var(--accent-2) 14%, var(--surface));
    }
    .msg.assistant {
      align-self: flex-start;
    }
    .composer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 18px 28px;
      border-top: 1px solid var(--line);
      background: var(--surface);
    }
    textarea {
      resize: vertical;
      min-height: 54px;
      max-height: 160px;
      width: 100%;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--bg);
      color: var(--text);
      font: inherit;
    }
    .preview {
      display: grid;
      gap: 8px;
      margin-top: 10px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: color-mix(in srgb, var(--accent) 8%, var(--surface));
    }
    .preview dl {
      display: grid;
      grid-template-columns: 86px 1fr;
      gap: 6px 10px;
      margin: 0;
    }
    .preview dt { color: var(--muted); }
    .preview dd { margin: 0; }
    code {
      padding: 2px 5px;
      border-radius: 5px;
      background: color-mix(in srgb, var(--muted) 12%, transparent);
    }
    @media (max-width: 780px) {
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      section { min-height: 70vh; }
      .composer { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <aside>
      <h1>KGGM Assistant</h1>
      <p class="muted">Local Gemma + Google Calendar</p>
      <div class="status">
        <div class="pill"><span>Ollama</span><b id="ollamaStatus">Checking</b></div>
        <div class="pill"><span>Google</span><b id="googleStatus">Checking</b></div>
        <div class="pill"><span>Model</span><b id="modelName"></b></div>
      </div>
      <button class="btn primary" id="connectBtn">Connect Google Calendar</button>
      <p class="muted" style="margin-top:18px">Try: <code>明天早上有什麼行程？</code></p>
      <p class="muted">Try: <code>幫我加一個牙醫</code>，再用下一句補時間與地點。</p>
    </aside>
    <section>
      <header>
        <h1>Calendar Command</h1>
        <p class="muted">新增活動前會先預覽，按確認才寫入 Google Calendar。</p>
      </header>
      <div class="chat" id="chat"></div>
      <form class="composer" id="form">
        <textarea id="input" placeholder="用自然語言描述活動，例如：明天下午 4 點和 Alex 開 30 分鐘會議"></textarea>
        <button class="btn primary" id="sendBtn" type="submit">Send</button>
      </form>
    </section>
  </main>
  <script>
    const chat = document.getElementById("chat");
    const form = document.getElementById("form");
    const input = document.getElementById("input");
    const sendBtn = document.getElementById("sendBtn");
    const connectBtn = document.getElementById("connectBtn");
    let pendingEvent = null;

    function addMessage(role, text, eventPreview, events) {
      const el = document.createElement("div");
      el.className = `msg ${role}`;
      el.textContent = text;
      if (eventPreview) {
        const p = document.createElement("div");
        p.className = "preview";
        p.innerHTML = `
          <h2>Event Preview</h2>
          <dl>
            <dt>Title</dt><dd>${escapeHtml(eventPreview.summary || "")}</dd>
            <dt>Start</dt><dd>${escapeHtml(eventPreview.start || "")}</dd>
            <dt>End</dt><dd>${escapeHtml(eventPreview.end || "")}</dd>
            <dt>Location</dt><dd>${escapeHtml(eventPreview.location || "")}</dd>
          </dl>
          <button class="btn primary" id="confirmBtn">Create Event</button>
        `;
        el.appendChild(p);
      }
      if (events && events.length) {
        const list = document.createElement("div");
        list.className = "preview";
        const items = events.map(ev => `
          <dt>${escapeHtml(ev.start || "")}</dt>
          <dd>${escapeHtml(ev.summary || "(no title)")}${ev.location ? " · " + escapeHtml(ev.location) : ""}</dd>
        `).join("");
        list.innerHTML = `<h2>Calendar Results</h2><dl>${items}</dl>`;
        el.appendChild(list);
      }
      chat.appendChild(el);
      chat.scrollTop = chat.scrollHeight;
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[c]));
    }

    async function refreshStatus() {
      const res = await fetch("/api/status");
      const data = await res.json();
      document.getElementById("ollamaStatus").textContent = data.ollama.ok ? "Ready" : "Offline";
      document.getElementById("ollamaStatus").className = data.ollama.ok ? "ok" : "bad";
      const googleReady = data.google.connected && !data.google.needsReconnect;
      document.getElementById("googleStatus").textContent = googleReady ? "Connected" : (data.google.connected ? "Reconnect needed" : "Not connected");
      document.getElementById("googleStatus").className = googleReady ? "ok" : "bad";
      document.getElementById("modelName").textContent = data.model;
      connectBtn.style.display = googleReady ? "none" : "block";
    }

    connectBtn.addEventListener("click", () => {
      window.location.href = "/auth/google";
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      addMessage("user", text);
      sendBtn.disabled = true;
      try {
        const res = await fetch("/api/message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed");
        pendingEvent = data.event || null;
        addMessage("assistant", data.reply, pendingEvent, data.events || []);
      } catch (err) {
        addMessage("assistant", `Error: ${err.message}`);
      } finally {
        sendBtn.disabled = false;
      }
    });

    chat.addEventListener("click", async (e) => {
      if (e.target.id !== "confirmBtn" || !pendingEvent) return;
      e.target.disabled = true;
      try {
        const res = await fetch("/api/create-event", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ event: pendingEvent })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Create failed");
        pendingEvent = null;
        addMessage("assistant", `已建立活動：${data.htmlLink || data.id}`);
      } catch (err) {
        addMessage("assistant", `Error: ${err.message}`);
      }
    });

    refreshStatus();
    addMessage("assistant", "我可以查詢行事曆，也可以用多輪對話補完活動資訊。新增活動前會先預覽，按確認才寫入。");
  </script>
</body>
</html>
"""


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler, status, text, content_type="text/plain; charset=utf-8"):
    body = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def token_exists():
    return TOKEN_FILE.exists()


def load_token():
    if not TOKEN_FILE.exists():
        return {}
    return json.loads(TOKEN_FILE.read_text())


def save_token(data):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        TOKEN_FILE.chmod(0o600)
    except OSError:
        pass


def http_json(url, payload=None, headers=None, method=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def form_post(url, payload, timeout=30):
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def google_configured():
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def token_scopes(token=None):
    token = token if token is not None else load_token()
    return set((token.get("scope") or "").split())


def missing_query_scopes():
    if not token_exists():
        return []
    scopes = token_scopes()
    return [] if REQUIRED_QUERY_SCOPE in scopes else [REQUIRED_QUERY_SCOPE]


def google_status():
    missing = missing_query_scopes()
    return {
        "configured": google_configured(),
        "connected": token_exists(),
        "needsReconnect": bool(missing),
        "missingScopes": missing,
    }


def google_auth_url():
    if not google_configured():
        raise RuntimeError("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET first.")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = secrets.token_urlsafe(24)
    OAUTH_STATE_FILE.write_text(state, encoding="utf-8")
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{APP_ORIGIN}/oauth2callback",
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def exchange_code(code):
    return form_post("https://oauth2.googleapis.com/token", {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": f"{APP_ORIGIN}/oauth2callback",
        "grant_type": "authorization_code",
    })


def refresh_access_token(token):
    refreshed = form_post("https://oauth2.googleapis.com/token", {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": token.get("refresh_token", ""),
        "grant_type": "refresh_token",
    })
    token.update(refreshed)
    save_token(token)
    return token


def valid_access_token():
    token = load_token()
    if not token:
        raise RuntimeError("Google Calendar is not connected.")
    if "refresh_token" in token:
        return refresh_access_token(token).get("access_token")
    return token.get("access_token")


def create_google_event(event):
    access_token = valid_access_token()
    calendar_id = urllib.parse.quote(GOOGLE_CALENDAR_ID, safe="")
    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    payload = {
        "summary": event["summary"],
        "start": {"dateTime": event["start"], "timeZone": event.get("timeZone", TIMEZONE)},
        "end": {"dateTime": event["end"], "timeZone": event.get("timeZone", TIMEZONE)},
    }
    if event.get("location"):
        payload["location"] = event["location"]
    if event.get("description"):
        payload["description"] = event["description"]
    return http_json(url, payload, headers={"Authorization": f"Bearer {access_token}"})


def list_google_events(time_min, time_max, query=""):
    access_token = valid_access_token()
    events = []
    for calendar in calendar_targets(access_token):
        calendar_id = urllib.parse.quote(calendar["id"], safe="")
        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "20",
        }
        if query:
            params["q"] = query
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events?{urllib.parse.urlencode(params)}"
        data = http_json(url, headers={"Authorization": f"Bearer {access_token}"})
        for item in data.get("items", []):
            events.append(format_calendar_event(item, calendar.get("summary", "")))
    events.sort(key=lambda item: item.get("start", ""))
    return events[:20]


def calendar_targets(access_token):
    if GOOGLE_CALENDAR_ID != "primary":
        return [{"id": GOOGLE_CALENDAR_ID, "summary": GOOGLE_CALENDAR_ID}]
    missing = missing_query_scopes()
    if missing:
        raise RuntimeError("Google Calendar 權限需要更新。請按左側 Connect Google Calendar 重新連接一次，授權讀取行事曆後才能查詢既有行程。")
    url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
    data = http_json(url, headers={"Authorization": f"Bearer {access_token}"})
    calendars = [
        {"id": item["id"], "summary": item.get("summary", item["id"])}
        for item in data.get("items", [])
        if item.get("selected") or item.get("primary")
    ]
    return calendars or [{"id": "primary", "summary": "primary"}]


def format_calendar_event(item, calendar_summary=""):
    start = item.get("start", {})
    end = item.get("end", {})
    return {
        "id": item.get("id", ""),
        "summary": item.get("summary", "(no title)"),
        "start": start.get("dateTime") or start.get("date", ""),
        "end": end.get("dateTime") or end.get("date", ""),
        "location": item.get("location", ""),
        "htmlLink": item.get("htmlLink", ""),
        "calendar": calendar_summary,
    }


def ollama_status():
    try:
        http_json(f"{OLLAMA_URL}/api/tags", timeout=2)
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Model did not return JSON.")
    return json.loads(text[start:end + 1])


def plan_with_ollama(user_text):
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    context = {
        "pending_event": SESSION.get("pending_event"),
        "recent_messages": SESSION.get("messages", [])[-8:],
    }
    system = f"""You are a local calendar assistant for one user.
Return only valid JSON, no markdown.
Current datetime is {now}. Default timezone is {TIMEZONE}.

You can do three things:
1. propose: propose one Google Calendar event to create.
2. query: query existing Google Calendar events in a date/time range.
3. ask: ask for missing information.

Use Traditional Chinese in reply.
Use ISO-8601 local datetimes with timezone offset.
If the user is answering a previous question, merge their answer with pending_event.
If creating an event and duration is missing, default to 60 minutes.
If creating an event and date or start time is missing, ask one concise follow-up question.
If querying events and range is vague but inferable, choose a sensible range:
- "今天": today 00:00 to tomorrow 00:00
- "明天": tomorrow 00:00 to the day after 00:00
- "早上": 06:00 to 12:00
- "下午": 12:00 to 18:00
- "晚上": 18:00 to 23:59

Schema:
{{
  "action": "propose" | "ask" | "query",
  "reply": "brief Traditional Chinese response",
  "event": {{
    "summary": "short title",
    "start": "YYYY-MM-DDTHH:MM:SS+08:00",
    "end": "YYYY-MM-DDTHH:MM:SS+08:00",
    "timeZone": "{TIMEZONE}",
    "location": "",
    "description": ""
  }},
  "query": {{
    "timeMin": "YYYY-MM-DDTHH:MM:SS+08:00",
    "timeMax": "YYYY-MM-DDTHH:MM:SS+08:00",
    "q": ""
  }},
  "draft": {{
    "summary": "",
    "date": "",
    "time": "",
    "duration_minutes": null,
    "location": "",
    "description": ""
  }},
  "questions": []
}}

Current conversation state:
{json.dumps(context, ensure_ascii=False)}
"""
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        "options": {"temperature": 0.1, "num_predict": 700},
    }
    data = http_json(f"{OLLAMA_URL}/api/chat", payload, timeout=180)
    content = data.get("message", {}).get("content", "")
    parsed = extract_json(content)
    if parsed.get("action") == "propose":
        normalize_event(parsed["event"])
    elif parsed.get("action") == "query":
        normalize_query(parsed["query"])
    return parsed


def normalize_query(query):
    for key in ["timeMin", "timeMax"]:
        if not query.get(key):
            raise ValueError(f"Missing query.{key}")
        dt.datetime.fromisoformat(query[key])
    query.setdefault("q", "")


def normalize_event(event):
    required = ["summary", "start", "end"]
    for key in required:
        if not event.get(key):
            raise ValueError(f"Missing event.{key}")
    dt.datetime.fromisoformat(event["start"])
    dt.datetime.fromisoformat(event["end"])
    event.setdefault("timeZone", TIMEZONE)
    event.setdefault("location", "")
    event.setdefault("description", "")


def now_local():
    return dt.datetime.now().astimezone()


def day_bounds(offset_days=0):
    base = now_local() + dt.timedelta(days=offset_days)
    start = base.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + dt.timedelta(days=1)


def parse_relative_day(text):
    if "後天" in text:
        return 2
    if "明天" in text or "明早" in text:
        return 1
    if "昨天" in text:
        return -1
    if any(word in text for word in ["今天", "今晚", "現在"]):
        return 0
    return None


def query_range(text):
    start_today, _ = day_bounds(0)
    two_day_words = ["今天與明天", "今天和明天", "今天、明天", "今天明天", "這兩天", "接下來兩天", "未來兩天"]
    if any(word in text for word in two_day_words):
        return start_today, start_today + dt.timedelta(days=2)
    match = re.search(r"(?:接下來|未來)(\d+)\s*天", text)
    if match:
        days = max(1, min(int(match.group(1)), 14))
        return start_today, start_today + dt.timedelta(days=days)
    match = re.search(r"(?:接下來|未來)(一|二|兩|三|四|五|六|七|八|九|十)\s*天", text)
    if match:
        days = chinese_number_to_int(match.group(1))
        if days:
            return start_today, start_today + dt.timedelta(days=min(days, 14))
    day_offset = parse_relative_day(text)
    if day_offset is None:
        return None
    return day_bounds(day_offset)


def apply_day_part(text, start, end):
    if any(word in text for word in ["早上", "上午", "明早"]):
        return start.replace(hour=6), start.replace(hour=12)
    if "中午" in text:
        return start.replace(hour=11), start.replace(hour=14)
    if "下午" in text:
        return start.replace(hour=12), start.replace(hour=18)
    if any(word in text for word in ["晚上", "今晚"]):
        return start.replace(hour=18), start.replace(hour=23, minute=59, second=59)
    return start, end


def fast_query(text):
    query_words = ["行程", "有什麼", "有哪些", "查", "看看", "空嗎", "忙嗎"]
    if not any(word in text for word in query_words):
        return None
    date_range = query_range(text)
    if date_range is None:
        return None
    start, end = date_range
    if (end - start) <= dt.timedelta(days=1):
        start, end = apply_day_part(text, start, end)
    return {
        "timeMin": start.isoformat(timespec="seconds"),
        "timeMax": end.isoformat(timespec="seconds"),
        "q": "",
    }


def chinese_number_to_int(value):
    mapping = {
        "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
    }
    return mapping.get(value)


def parse_time_of_day(text):
    match = re.search(r"(\d{1,2})(?:[:：](\d{1,2})|\s*點)", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
    else:
        match = re.search(r"(一|二|兩|三|四|五|六|七|八|九|十|十一|十二)\s*點", text)
        if not match:
            return None
        hour = chinese_number_to_int(match.group(1))
        minute = 0
    if hour is None or hour > 23 or minute > 59:
        return None
    if any(word in text for word in ["下午", "晚上"]) and hour < 12:
        hour += 12
    if any(word in text for word in ["中午"]) and hour < 11:
        hour += 12
    return hour, minute


def parse_duration_minutes(text):
    match = re.search(r"(\d+(?:\.\d+)?)\s*小時", text)
    if match:
        return int(float(match.group(1)) * 60)
    match = re.search(r"(\d+)\s*分鐘", text)
    if match:
        return int(match.group(1))
    return 60


def clean_summary(text):
    summary = text
    for word in ["幫我", "請", "加一個", "加", "新增", "建立", "安排", "預約", "排"]:
        summary = summary.replace(word, "")
    summary = summary.strip(" ，,。")
    return summary or "未命名活動"


def parse_location(text):
    match = re.search(r"在([^，,。]+)", text)
    if not match:
        return ""
    return match.group(1).strip()


def fast_complete_pending_event(text):
    pending = SESSION.get("pending_event")
    if not pending:
        return None
    day_offset = parse_relative_day(text)
    time_value = parse_time_of_day(text)
    if day_offset is None or time_value is None:
        return None
    start_day, _ = day_bounds(day_offset)
    hour, minute = time_value
    start = start_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
    end = start + dt.timedelta(minutes=parse_duration_minutes(text))
    summary = pending.get("summary") or "未命名活動"
    if summary.startswith(("幫我", "請")) or any(word in summary for word in ["加", "新增", "建立"]):
        summary = clean_summary(summary)
    event = {
        "summary": summary,
        "start": start.isoformat(timespec="seconds"),
        "end": end.isoformat(timespec="seconds"),
        "timeZone": TIMEZONE,
        "location": parse_location(text) or pending.get("location", ""),
        "description": pending.get("description", ""),
    }
    normalize_event(event)
    return event


def remember(role, content):
    SESSION["messages"].append({"role": role, "content": content})
    SESSION["messages"] = SESSION["messages"][-12:]


def looks_like_incomplete_create(user_text):
    create_words = ["加", "新增", "建立", "安排", "預約", "約", "排"]
    time_words = [
        "今天", "明天", "後天", "昨天", "週", "星期", "禮拜", "下週", "這週",
        "上午", "下午", "晚上", "早上", "中午", "今晚", "明早",
        "點", ":", "：", "分鐘", "小時", "月", "日", "號",
    ]
    return any(word in user_text for word in create_words) and not any(word in user_text for word in time_words)


def reply_for_events(events, query):
    if not events:
        return "這段時間沒有找到行程。"
    start = query.get("timeMin", "")
    end = query.get("timeMax", "")
    return f"找到 {len(events)} 個行程（{start} 到 {end}）："


def handle_user_message(user_text):
    remember("user", user_text)
    event = fast_complete_pending_event(user_text)
    if event:
        SESSION["pending_event"] = event
        reply = "我整理好活動資訊了，請確認是否建立。"
        remember("assistant", reply)
        return {"action": "propose", "reply": reply, "event": event, "questions": []}

    quick_query = fast_query(user_text)
    if quick_query:
        try:
            events = list_google_events(quick_query["timeMin"], quick_query["timeMax"], quick_query.get("q", ""))
        except RuntimeError as exc:
            reply = str(exc)
            remember("assistant", reply)
            return {"action": "ask", "reply": reply, "questions": []}
        reply = reply_for_events(events, quick_query)
        remember("assistant", reply)
        return {"action": "query", "reply": reply, "events": events, "query": quick_query}

    if not SESSION.get("pending_event") and looks_like_incomplete_create(user_text):
        draft = {
            "summary": clean_summary(user_text),
            "date": "",
            "time": "",
            "duration_minutes": None,
            "location": "",
            "description": "",
        }
        SESSION["pending_event"] = draft
        reply = "可以，請告訴我這個活動的日期、時間，還有需要的話地點與多久。"
        remember("assistant", reply)
        return {"action": "ask", "reply": reply, "questions": ["日期與開始時間是什麼？"]}
    try:
        parsed = plan_with_ollama(user_text)
    except Exception:
        reply = "我這句沒有穩定解析成功。請換個更明確的說法，例如「今天與明天有哪些行程」或「明天下午三點加一個牙醫」。"
        remember("assistant", reply)
        return {"action": "ask", "reply": reply, "questions": []}
    action = parsed.get("action")

    if action == "propose":
        event = parsed.get("event", {})
        SESSION["pending_event"] = event
        reply = parsed.get("reply") or "我整理好活動資訊了，請確認是否建立。"
        remember("assistant", reply)
        return {"action": "propose", "reply": reply, "event": event, "questions": []}

    if action == "query":
        query = parsed.get("query", {})
        try:
            events = list_google_events(query["timeMin"], query["timeMax"], query.get("q", ""))
        except RuntimeError as exc:
            reply = str(exc)
            remember("assistant", reply)
            return {"action": "ask", "reply": reply, "questions": []}
        model_reply = parsed.get("reply") or ""
        result_reply = reply_for_events(events, query)
        reply = result_reply if not model_reply else f"{model_reply}\n{result_reply}"
        remember("assistant", reply)
        return {"action": "query", "reply": reply, "events": events, "query": query}

    draft = parsed.get("draft") or SESSION.get("pending_event")
    if draft:
        SESSION["pending_event"] = draft
    questions = parsed.get("questions") or []
    reply = parsed.get("reply") or "我還需要更多資訊。"
    remember("assistant", reply)
    return {"action": "ask", "reply": reply, "questions": questions}


class Handler(BaseHTTPRequestHandler):
    server_version = "KGGMCalendarAssistant/0.1"

    def do_HEAD(self):
        path, _, _ = self.path.partition("?")
        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
        elif path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/":
            text_response(self, 200, INDEX_HTML, "text/html; charset=utf-8")
        elif path == "/api/status":
            json_response(self, 200, {
                "model": MODEL,
                "ollama": ollama_status(),
                "google": google_status(),
            })
        elif path == "/auth/google":
            try:
                url = google_auth_url()
            except Exception as exc:
                text_response(self, 400, f"Google OAuth not configured: {exc}")
                return
            self.send_response(302)
            self.send_header("Location", url)
            self.end_headers()
        elif path == "/oauth2callback":
            params = urllib.parse.parse_qs(query)
            state = params.get("state", [""])[0]
            expected = OAUTH_STATE_FILE.read_text(encoding="utf-8") if OAUTH_STATE_FILE.exists() else ""
            if not state or state != expected:
                text_response(self, 400, "OAuth state mismatch.")
                return
            if "error" in params:
                text_response(self, 400, params["error"][0])
                return
            try:
                token = exchange_code(params.get("code", [""])[0])
                save_token(token)
            except Exception as exc:
                text_response(self, 500, f"Token exchange failed: {exc}")
                return
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            text_response(self, 404, "Not found")

    def do_POST(self):
        try:
            if self.path in ("/api/message", "/api/parse"):
                body = read_json(self)
                text = body.get("text", "").strip()
                if not text:
                    json_response(self, 400, {"error": "Missing text"})
                    return
                result = handle_user_message(text)
                json_response(self, 200, result)
            elif self.path == "/api/create-event":
                body = read_json(self)
                event = body.get("event", {})
                normalize_event(event)
                created = create_google_event(event)
                SESSION["pending_event"] = None
                remember("assistant", f"已建立活動：{created.get('summary', event.get('summary', ''))}")
                json_response(self, 200, {
                    "id": created.get("id"),
                    "htmlLink": created.get("htmlLink"),
                })
            else:
                json_response(self, 404, {"error": "Not found"})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            json_response(self, exc.code, {"error": detail})
        except Exception as exc:
            json_response(self, 500, {"error": str(exc)})

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


def ensure_localhost_available():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        if sock.connect_ex((APP_HOST, APP_PORT)) == 0:
            raise SystemExit(f"{APP_ORIGIN} is already in use. Set KGGM_PORT to another port.")


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_localhost_available()
    print(f"KGGM assistant running at {APP_ORIGIN}")
    print(f"Using Ollama model: {MODEL}")
    ThreadingHTTPServer((APP_HOST, APP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
