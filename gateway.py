"""Agent gateway: one Slack app per person, many agents behind it as registry entries.

Slack side: Socket Mode (outbound only). Local side: HTTP on 127.0.0.1 guarded by a
bearer token, used by the Claude skill to register, send, read the inbox and deregister.
Incoming Slack text is stored as untrusted data; nothing here executes it.
"""
import json
import os
import re
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

DB_PATH = os.environ.get("GATEWAY_DB", "gateway.db")
LOCAL_PORT = int(os.environ.get("GATEWAY_PORT", "8765"))
LOCAL_TOKEN = os.environ["GATEWAY_LOCAL_TOKEN"]
# Slack user IDs or bot IDs allowed to reach our agents, e.g. "U0123,B0456"
ALLOWED_SENDERS = {s for s in os.environ.get("ALLOWED_SENDERS", "").split(",") if s}
DEFAULT_TTL = 8 * 3600
PAIR_LIMIT = (6, 600)  # max messages per (sender, agent) pair per window seconds
ROUTE = re.compile(r"^\s*to:(\S+)\s+(.*)$", re.S)

app = App(token=os.environ["SLACK_BOT_TOKEN"])
db_lock = threading.Lock()
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.executescript(
    """
    CREATE TABLE IF NOT EXISTS agents(
      name TEXT PRIMARY KEY, owner TEXT, summary TEXT, expires_at REAL);
    CREATE TABLE IF NOT EXISTS inbox(
      id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, sender TEXT, channel TEXT,
      text TEXT, ts REAL, read INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS rate(sender TEXT, agent TEXT, ts REAL);
    """
)


def live_agent(name):
    row = db.execute("SELECT expires_at FROM agents WHERE name=?", (name,)).fetchone()
    return bool(row) and row[0] > time.time()


def over_limit(sender, agent):
    count, window = PAIR_LIMIT
    now = time.time()
    db.execute("DELETE FROM rate WHERE ts<?", (now - window,))
    n = db.execute(
        "SELECT COUNT(*) FROM rate WHERE sender=? AND agent=?", (sender, agent)
    ).fetchone()[0]
    if n >= count:
        return True
    db.execute("INSERT INTO rate VALUES(?,?,?)", (sender, agent, now))
    return False


@app.event("message")
def on_message(event, logger):
    sender = event.get("user") or event.get("bot_id")
    if not sender or sender not in ALLOWED_SENDERS:
        return
    match = ROUTE.match(event.get("text", ""))
    if not match:
        return
    agent, text = match.group(1), match.group(2).strip()
    label = event.get("username") or sender
    with db_lock:
        if not live_agent(agent) or over_limit(sender, agent):
            return
        db.execute(
            "INSERT INTO inbox(agent,sender,channel,text,ts) VALUES(?,?,?,?,?)",
            (agent, label, event["channel"], text, time.time()),
        )
        db.commit()


class Local(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def _authed(self):
        if self.headers.get("Authorization") != f"Bearer {LOCAL_TOKEN}":
            self._reply(401, {"error": "unauthorized"})
            return False
        return True

    def do_GET(self):
        if not self._authed():
            return
        url = urlparse(self.path)
        with db_lock:
            if url.path == "/agents":
                rows = db.execute(
                    "SELECT name,owner,summary,expires_at FROM agents WHERE expires_at>?",
                    (time.time(),),
                ).fetchall()
                return self._reply(200, [dict(zip(("name", "owner", "summary", "expires_at"), r)) for r in rows])
            if url.path == "/inbox":
                agent = parse_qs(url.query).get("agent", [""])[0]
                rows = db.execute(
                    "SELECT id,sender,channel,text,ts FROM inbox WHERE agent=? AND read=0 ORDER BY id",
                    (agent,),
                ).fetchall()
                db.execute("UPDATE inbox SET read=1 WHERE agent=? AND read=0", (agent,))
                db.commit()
                return self._reply(200, [dict(zip(("id", "sender", "channel", "text", "ts"), r)) for r in rows])
        self._reply(404, {"error": "not found"})

    def do_POST(self):
        if not self._authed():
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        path = urlparse(self.path).path
        if path == "/register":
            ttl = int(body.get("ttl", DEFAULT_TTL))
            with db_lock:
                db.execute(
                    "INSERT OR REPLACE INTO agents VALUES(?,?,?,?)",
                    (body["name"], body.get("owner", ""), body.get("summary", ""), time.time() + ttl),
                )
                db.commit()
            return self._reply(200, {"ok": True, "expires_in": ttl})
        if path == "/deregister":
            with db_lock:
                db.execute("DELETE FROM agents WHERE name=?", (body["name"],))
                db.commit()
            return self._reply(200, {"ok": True})
        if path == "/send":
            with db_lock:
                if not live_agent(body["from"]):
                    return self._reply(403, {"error": "agent not registered"})
            app.client.chat_postMessage(
                channel=body["channel"],
                text=f"to:{body['to']} {body['text']}",
                username=body["from"],
                icon_emoji=":robot_face:",
            )
            return self._reply(200, {"ok": True})
        self._reply(404, {"error": "not found"})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", LOCAL_PORT), Local)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
