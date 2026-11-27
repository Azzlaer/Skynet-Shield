"""Single-process Shield API prototype, behind a trusted TLS reverse proxy."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from Server.registry import load_registry, validate_registry
from contextlib import closing
from http import HTTPStatus

HEX = re.compile(r"[0-9a-f]{64}")
SESSION = re.compile(r"[A-Za-z0-9_-]{1,64}")
EVENTS = {"integrity_mismatch", "module_unlisted", "memory_mismatch", "regular_timing_review"}
MAX_BODY = 4096

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError("Non-finite JSON value")

class Store:
    def __init__(self, path, ttl=300, capacity=10000, clock=time.time):
        if not 1 <= ttl <= 86400 or not 1 <= capacity <= 100000:
            raise ValueError("Invalid limits")
        self.path, self.ttl, self.capacity, self.clock = path, ttl, capacity, clock
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            # Explicit migration: old sessions belong to the legacy default instance.
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'").fetchone() and not any(r[1]=="server_id" for r in db.execute("PRAGMA table_info(sessions)")):
                db.execute("ALTER TABLE sessions RENAME TO sessions_v1")
                db.execute("CREATE TABLE sessions (token_hash BLOB PRIMARY KEY, game_session TEXT NOT NULL, server_id TEXT NOT NULL, expires REAL NOT NULL, seq TEXT NOT NULL, last_seen REAL, UNIQUE(server_id,game_session))")
                # Invalidate old grants on upgrade; require authenticated reissue.
                db.execute("DROP TABLE sessions_v1")
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'").fetchone() and not any(r[1]=="server_id" for r in db.execute("PRAGMA table_info(events)")):
                db.execute("ALTER TABLE events ADD COLUMN server_id TEXT NOT NULL DEFAULT 'default'")
            db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash BLOB PRIMARY KEY, game_session TEXT NOT NULL, server_id TEXT NOT NULL,
                    expires REAL NOT NULL, seq TEXT NOT NULL, last_seen REAL,
                    UNIQUE(server_id, game_session)
                )""")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, created REAL NOT NULL,
                    game_session TEXT NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL,
                    server_id TEXT NOT NULL
                )
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    @staticmethod
    def key(token):
        return hashlib.sha256(token.encode("ascii")).digest()

    def issue(self, session, server_id="default"):
        if not isinstance(session, str) or not SESSION.fullmatch(session) or not isinstance(server_id,str) or not SESSION.fullmatch(server_id):
            raise ValueError("Invalid game session")
        token = secrets.token_hex(32)
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            now = self.clock()
            db.execute("DELETE FROM sessions WHERE expires <= ?", (now,))
            db.execute("DELETE FROM sessions WHERE game_session = ? AND server_id = ?", (session,server_id))
            if db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] >= self.capacity:
                raise OverflowError("Capacity reached")
            db.execute("INSERT INTO sessions(token_hash,game_session,server_id,expires,seq,last_seen) VALUES (?, ?, ?, ?, ?, NULL)",
                       (self.key(token), session, server_id, now+self.ttl, "0"))
        return token

    def accept(self, token, sequence, event=None, allowed_servers=None):
        if (not isinstance(token, str) or not HEX.fullmatch(token) or
            type(sequence) is not int or not 0 < sequence < 2**64 or
            (event is not None and (not isinstance(event, str) or event not in EVENTS))):
            return False
        key = self.key(token)
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            now = self.clock()
            row = db.execute("SELECT game_session,expires,seq,server_id FROM sessions WHERE token_hash=?", (key,)).fetchone()
            if not row or row[1] <= now or sequence <= int(row[2]) or (allowed_servers is not None and row[3] not in allowed_servers):
                return False
            db.execute("UPDATE sessions SET seq=?,last_seen=? WHERE token_hash=?",
                       (str(sequence), now, key))
            if event:
                # Keep a bounded history; client reports are explicitly untrusted.
                db.execute("INSERT INTO events(created,game_session,kind,source,server_id) VALUES (?,?,?,?,?)",
                           (now,row[0],event,"client_unverified",row[3]))
                db.execute("DELETE FROM events WHERE id <= (SELECT COALESCE(MAX(id),0)-10000 FROM events)")
        return True

    def revoke(self, session, server_id="default"):
        if not isinstance(session, str) or not SESSION.fullmatch(session):
            raise ValueError("Invalid game session")
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM sessions WHERE game_session=? AND server_id=?", (session,server_id))

    def overview(self, allowed_servers=None):
        with closing(self.connect()) as db:
            counts = db.execute("SELECT server_id,COUNT(*) FROM sessions WHERE expires > ? GROUP BY server_id", (self.clock(),)).fetchall()
            active = sum(n for sid,n in counts if allowed_servers is None or sid in allowed_servers)
            events = db.execute("SELECT id,created,game_session,kind,source,server_id FROM events ORDER BY id DESC LIMIT 100").fetchall()
        return {"active_sessions":active,"events":[dict(zip(("id","created","game_session","kind","source","server_id"), row)) for row in events]}

def make_app(store, game_key, admin_key):
    registry = validate_registry({"default": game_key} if isinstance(game_key,str) else game_key, admin_key)
    # Remove grants for unregistered instances at startup, preventing revival on re-add.
    with closing(store.connect()) as db, db:
        marks = ",".join("?" for _ in registry)
        db.execute("DELETE FROM sessions WHERE server_id NOT IN (" + marks + ")", tuple(registry))
    def identify(token):
        return next((sid for sid,key in registry.items() if hmac.compare_digest(token.encode(),key.encode())), None)

    def app(env, start):
        def respond(code, obj=None):
            body = b"" if obj is None else json.dumps(obj, separators=(",",":")).encode()
            start(f"{code} {HTTPStatus(code).phrase}", [("Content-Type","application/json"),("Content-Length",str(len(body))),("Cache-Control","no-store")])
            return [body]
        auth = env.get("HTTP_AUTHORIZATION","")
        token = auth[7:] if isinstance(auth,str) and len(auth)==71 and auth.startswith("Bearer ") else ""
        method, path = env.get("REQUEST_METHOD"),env.get("PATH_INFO")
        try:
            if not HEX.fullmatch(token):
                return respond(401)
            if method == "GET" and path in ("/v1/admin/overview","/v1/admin/servers","/v1/admin/sessions"):
                if not hmac.compare_digest(token.encode(),admin_key.encode()):
                    return respond(401)
                if path.endswith("/servers"):
                    with closing(store.connect()) as db:
                        counts=dict(db.execute("SELECT server_id,COUNT(*) FROM sessions WHERE expires>? GROUP BY server_id",(store.clock(),)))
                    return respond(200,{"servers":[{"server_id":sid,"active_sessions":counts.get(sid,0)} for sid in sorted(registry)]})
                if path.endswith("/sessions"):
                    with closing(store.connect()) as db:
                        ids = sorted(registry)
                        marks = ",".join("?" for _ in ids)
                        rows = db.execute("SELECT server_id,game_session,expires,last_seen FROM sessions WHERE expires>? AND server_id IN ("+marks+") ORDER BY expires DESC,server_id,game_session LIMIT 501",(store.clock(),*ids)).fetchall()
                    return respond(200,{"sessions":[dict(zip(("server_id","game_session","expires","last_seen"),row)) for row in rows[:500]],"truncated":len(rows)>500})
                return respond(200,store.overview(registry))
            if method != "POST" or path not in ("/v1/session/issue","/v1/session/revoke","/v1/heartbeat","/v1/events"):
                return respond(404)
            server_id = identify(token) if path.startswith("/v1/session/") else None
            if path.startswith("/v1/session/") and server_id is None:
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
            obj = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
            if not isinstance(obj,dict):
                return respond(400)
            if path.startswith("/v1/session/"):
                if set(obj) != {"game_session"}:
                    return respond(400)
                if path.endswith("/issue"):
                    return respond(201,{"token":store.issue(obj["game_session"],server_id),"expires_in":store.ttl})
                store.revoke(obj["game_session"],server_id)
                return respond(204)
            if path == "/v1/heartbeat" and set(obj) == {"sequence"}:
                return respond(204 if store.accept(token,obj["sequence"],allowed_servers=registry) else 401)
            if path == "/v1/events" and set(obj) == {"sequence","kind"}:
                if not isinstance(obj["kind"],str) or obj["kind"] not in EVENTS:
                    return respond(400)
                return respond(204 if store.accept(token,obj["sequence"],obj["kind"],registry) else 401)
            return respond(400)
        except (ValueError,TypeError,UnicodeError,RecursionError):
            return respond(400)
        except OverflowError:
            return respond(503)
        except sqlite3.Error:
            return respond(503)
    return app

def application_from_env():
    return make_app(Store(os.environ.get("SHIELD_DB","shield.sqlite3")),
                    load_registry(os.environ),os.environ["SHIELD_ADMIN_KEY"])
