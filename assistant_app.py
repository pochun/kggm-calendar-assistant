#!/usr/bin/env python3
import base64
import datetime as dt
import html
import json
import os
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
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


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
      <p class="muted" style="margin-top:18px">Try: <code>下週二下午三點幫我加一個牙醫，地點台大醫院，1 小時</code></p>
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

    function addMessage(role, text, eventPreview) {
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
      document.getElementById("googleStatus").textContent = data.google.connected ? "Connected" : "Not connected";
      document.getElementById("googleStatus").className = data.google.connected ? "ok" : "bad";
      document.getElementById("modelName").textContent = data.model;
      connectBtn.style.display = data.google.connected ? "none" : "block";
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
        const res = await fetch("/api/parse", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed");
        pendingEvent = data.event || null;
        addMessage("assistant", data.reply, pendingEvent);
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
    addMessage("assistant", "我可以把自然語言轉成 Google Calendar 活動。先連接 Google Calendar，然後輸入活動描述。");
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


def parse_event_with_ollama(user_text):
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    system = f"""You convert a user's natural language request into one Google Calendar event.
Return only valid JSON, no markdown.
Current datetime is {now}. Default timezone is {TIMEZONE}.
If the request lacks a date or start time, return {{"action":"ask","reply":"...","questions":["..."]}}.
If duration is missing, default to 60 minutes.
Use ISO-8601 local datetimes with timezone offset for start and end.
Schema:
{{
  "action": "propose" | "ask",
  "reply": "brief Traditional Chinese response",
  "event": {{
    "summary": "short title",
    "start": "YYYY-MM-DDTHH:MM:SS+08:00",
    "end": "YYYY-MM-DDTHH:MM:SS+08:00",
    "timeZone": "{TIMEZONE}",
    "location": "",
    "description": ""
  }},
  "questions": []
}}
"""
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        "options": {"temperature": 0.1},
    }
    data = http_json(f"{OLLAMA_URL}/api/chat", payload, timeout=180)
    content = data.get("message", {}).get("content", "")
    parsed = extract_json(content)
    if parsed.get("action") == "propose":
        normalize_event(parsed["event"])
    return parsed


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
                "google": {"configured": google_configured(), "connected": token_exists()},
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
            if self.path == "/api/parse":
                body = read_json(self)
                text = body.get("text", "").strip()
                if not text:
                    json_response(self, 400, {"error": "Missing text"})
                    return
                parsed = parse_event_with_ollama(text)
                json_response(self, 200, parsed)
            elif self.path == "/api/create-event":
                body = read_json(self)
                event = body.get("event", {})
                normalize_event(event)
                created = create_google_event(event)
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
