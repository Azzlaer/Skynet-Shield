"""Reference adapter for an independently authenticated GameServer.
Never expose the service key to game clients.
"""
import json
import re
import ssl
import urllib.request
import urllib.parse
from dataclasses import dataclass

HEX = re.compile(r"[0-9a-f]{64}")
SESSION = re.compile(r"[A-Za-z0-9_-]{1,64}")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

@dataclass(frozen=True)
class Grant:
    token: str
    expires_in: int

class ShieldApi:
    def __init__(self, base, key):
        uri = urllib.parse.urlsplit(base)
        if (uri.scheme != "https" or not uri.hostname or uri.username is not None or
            uri.password is not None or uri.query or uri.fragment or uri.path not in ("","/") or
            not isinstance(key,str) or not HEX.fullmatch(key)):
            raise ValueError("Trusted HTTPS origin and service key required")
        self.base = base.rstrip("/")
        self.key = key
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            NoRedirect(), urllib.request.HTTPSHandler(context=context))

    def _post(self, route, session):
        if not isinstance(session,str) or not SESSION.fullmatch(session):
            raise ValueError("Invalid opaque session")
        request = urllib.request.Request(self.base+route,
            data=json.dumps({"game_session":session}).encode(),
            headers={"Authorization":"Bearer "+self.key,"Content-Type":"application/json"},
            method="POST")
        with self.opener.open(request,timeout=5) as response:
            body=response.read(4097)
            if len(body)>4096:
                raise ValueError("Oversized response")
            return response.status, body

    def issue_after_authenticated_login(self, game_session):
        # Caller MUST have authenticated the player and bound an opaque session ID.
        status, body = self._post("/v1/session/issue", game_session)
        if status != 201:
            raise ValueError("Unexpected issue response")
        grant=json.loads(body)
        token, ttl=grant["token"],grant["expires_in"]
        if not isinstance(token,str) or not HEX.fullmatch(token) or type(ttl) is not int or not 1<=ttl<=86400:
            raise ValueError("Invalid grant")
        return Grant(token,ttl)

    def revoke_on_logout(self, game_session):
        status,_=self._post("/v1/session/revoke",game_session)
        if status != 204:
            raise ValueError("Unexpected revoke response")
