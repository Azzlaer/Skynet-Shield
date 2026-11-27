"""Single-process Shield API prototype, behind a trusted TLS reverse proxy."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from http import HTTPStatus

HEX = re.compile(r"[0-9a-f]{64}")
SESSION = re.compile(r"[A-Za-z0-9_-]{1,64}")
EVENTS = {"integrity_mismatch", "module_unlisted", "memory_mismatch", "regular_timing_review"}
MAX_BODY = 4096

class Store:
    def __init__(self, path, ttl=300, capacity=10000, clock=time.time):
        if not 1 <= ttl <= 86400 or not 1 <= capacity <= 100000:
            raise ValueError("Invalid limits")
        self.path, self.ttl, self.capacity, self.clock = path, ttl, capacity, clock
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash BLOB PRIMARY KEY, game_session TEXT UNIQUE NOT NULL,
                    expires REAL NOT NULL, seq TEXT NOT NULL, last_seen REAL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, created REAL NOT NULL,
                    game_session TEXT NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL
                );
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    @staticmethod
    def key(token):
        return hashlib.sha256(token.encode("ascii")).digest()

    def issue(self, session):
        if not isinstance(session, str) or not SESSION.fullmatch(session):
            raise ValueError("Invalid game session")
        token = secrets.token_hex(32)
        now = self.clock()
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM sessions WHERE expires <= ?", (now,))
            db.execute("DELETE FROM sessions WHERE game_session = ?", (session,))
            if db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] >= self.capacity:
                raise OverflowError("Capacity reached")
            db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, NULL)",
                       (self.key(token), session, now+self.ttl, "0"))
        return token

    def accept(self, token, sequence, event=None):
        if (not isinstance(token, str) or not HEX.fullmatch(token) or
            type(sequence) is not int or not 0 < sequence < 2**64 or
            (event is not None and (not isinstance(event, str) or event not in EVENTS))):
            return False
        now = self.clock()
        key = self.key(token)
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT game_session,expires,seq FROM sessions WHERE token_hash=?", (key,)).fetchone()
            if not row or row[1] <= now or sequence <= int(row[2]):
                return False
            db.execute("UPDATE sessions SET seq=?,last_seen=? WHERE token_hash=?",
                       (str(sequence), now, key))
            if event:
                # Keep a bounded history; client reports are explicitly untrusted.
                db.execute("INSERT INTO events(created,game_session,kind,source) VALUES (?,?,?,?)",
                           (now,row[0],event,"client_unverified"))
                db.execute("DELETE FROM events WHERE id <= (SELECT COALESCE(MAX(id),0)-10000 FROM events)")
        return True

    def revoke(self, session):
        if not isinstance(session, str) or not SESSION.fullmatch(session):
            raise ValueError("Invalid game session")
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM sessions WHERE game_session=?", (session,))

    def overview(self):
        with closing(self.connect()) as db:
            active = db.execute("SELECT COUNT(*) FROM sessions WHERE expires > ?", (self.clock(),)).fetchone()[0]
            events = db.execute("SELECT id,created,game_session,kind,source FROM events ORDER BY id DESC LIMIT 100").fetchall()
        return {"active_sessions":active,"events":[dict(zip(("id","created","game_session","kind","source"), row)) for row in events]}

def make_app(store, game_key, admin_key):
    if not all(isinstance(k,str) and HEX.fullmatch(k) for k in (game_key,admin_key)) or game_key == admin_key:
        raise ValueError("Separate 256-bit hex keys required")

    def app(env, start):
        def respond(code, obj=None):
            body = b"" if obj is None else json.dumps(obj, separators=(",",":")).encode()
            start(f"{code} {HTTPStatus(code).phrase}", [("Content-Type","application/json"),("Content-Length",str(len(body))),("Cache-Control","no-store")])
            return [body]
        auth = env.get("HTTP_AUTHORIZATION","")
        token = auth[7:] if auth.startswith("Bearer ") else ""
        method, path = env.get("REQUEST_METHOD"),env.get("PATH_INFO")
        try:
            if method == "GET" and path == "/v1/admin/overview":
                if not hmac.compare_digest(token.encode(),admin_key.encode()):
                    return respond(401)
                return respond(200,store.overview())
            if method != "POST" or path not in ("/v1/session/issue","/v1/session/revoke","/v1/heartbeat","/v1/events"):
                return respond(404)
            if path.startswith("/v1/session/") and not hmac.compare_digest(token.encode(),game_key.encode()):
                return respond(401)
            if not HEX.fullmatch(token):
                return respond(401)
            if env.get("CONTENT_TYPE","").split(";")[0].strip().lower() != "application/json":
                return respond(415)
            length = int(env.get("CONTENT_LENGTH") or "0")
            if not 0 < length <= MAX_BODY:
                return respond(413)
            raw = env["wsgi.input"].read(length)
            if len(raw) != length:
                return respond(400)
            obj = json.loads(raw)
            if not isinstance(obj,dict):
                return respond(400)
            if path.startswith("/v1/session/"):
                if set(obj) != {"game_session"}:
                    return respond(400)
                if path.endswith("/issue"):
                    return respond(201,{"token":store.issue(obj["game_session"]),"expires_in":store.ttl})
                store.revoke(obj["game_session"])
                return respond(204)
            if path == "/v1/heartbeat" and set(obj) == {"sequence"}:
                return respond(204 if store.accept(token,obj["sequence"]) else 401)
            if path == "/v1/events" and set(obj) == {"sequence","kind"}:
                if not isinstance(obj["kind"],str) or obj["kind"] not in EVENTS:
                    return respond(400)
                return respond(204 if store.accept(token,obj["sequence"],obj["kind"]) else 401)
            return respond(400)
        except (ValueError,TypeError,UnicodeError):
            return respond(400)
        except OverflowError:
            return respond(503)
        except sqlite3.Error:
            return respond(503)
    return app

def application_from_env():
    return make_app(Store(os.environ.get("SHIELD_DB","shield.sqlite3")),
                    os.environ["SHIELD_GAME_KEY"],os.environ["SHIELD_ADMIN_KEY"])
