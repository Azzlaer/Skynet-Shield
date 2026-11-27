"""In-memory reference session validator; not an HTTP server."""
import secrets
import hashlib
import threading
import time

class SessionStore:
    def __init__(self, ttl=300, capacity=10000, clock=time.monotonic):
        if ttl <= 0 or capacity <= 0:
            raise ValueError("Invalid session limits")
        self.ttl, self.capacity, self.clock = ttl, capacity, clock
        self.sessions = {}
        self.lock = threading.Lock()

    def issue(self):
        # Invoke only after independent GameServer authentication.
        with self.lock:
            now = self.clock()
            self.sessions = {k: v for k, v in self.sessions.items() if v[0] > now}
            if len(self.sessions) >= self.capacity:
                raise RuntimeError("Session capacity reached")
            token = secrets.token_hex(32)
            self.sessions[self._key(token)] = (now + self.ttl, 0)
            return token

    @staticmethod
    def _key(token):
        return hashlib.sha256(token.encode("ascii")).digest()

    def heartbeat(self, token, sequence):
        if (not isinstance(token, str) or len(token) != 64 or
            any(c not in "0123456789abcdef" for c in token) or
            type(sequence) is not int or not 0 < sequence < 2**64):
            return False
        key = self._key(token)
        with self.lock:
            record = self.sessions.get(key)
            if record is None:
                return False
            expires, previous = record
            if expires <= self.clock():
                del self.sessions[key]
                return False
            if sequence <= previous:
                return False
            self.sessions[key] = (expires, sequence)
            return True

    def revoke(self, token):
        with self.lock:
            self.sessions.pop(self._key(token), None)
