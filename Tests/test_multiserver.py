import tempfile
import unittest
import sqlite3
from pathlib import Path
from Server.service import Store, make_app
from Server.registry import load_registry
from test_service import ServiceTests

class MultiTests(ServiceTests):
    def test_isolation(self):
        self.app=make_app(self.store,{"normal":self.game,"vip":"c"*64},self.admin)
        def issue(key):
            code,grant=self.request("/v1/session/issue",key,{"game_session":"same"})
            self.assertEqual(code,201)
            return grant["token"]
        a,b=issue(self.game),issue("c"*64)
        self.assertEqual(self.request("/v1/session/revoke",self.game,{"game_session":"same"})[0],204)
        self.assertEqual(self.request("/v1/heartbeat",a,{"sequence":1})[0],401)
        self.assertEqual(self.request("/v1/events",b,{"sequence":1,"kind":"module_unlisted"})[0],204)
        _,overview=self.request("/v1/admin/overview",self.admin,method="GET")
        self.assertEqual(overview["events"][0]["server_id"],"vip")
        _,servers=self.request("/v1/admin/servers",self.admin,method="GET")
        self.assertEqual(servers["servers"],[{"server_id":"normal","active_sessions":0},{"server_id":"vip","active_sessions":1}])
        self.app=make_app(self.store,{"normal":self.game},self.admin)
        self.assertEqual(self.request("/v1/heartbeat",b,{"sequence":2})[0],401)

    def test_registry(self):
        p=Path(self.tmp.name)/"servers.xml"
        p.write_text('<ShieldServers version="1"><Server id="vip" keyEnv="SHIELD_GAME_KEY_VIP"/></ShieldServers>')
        self.assertEqual(load_registry({"SHIELD_REGISTRY":str(p),"SHIELD_GAME_KEY_VIP":"c"*64}),{"vip":"c"*64})
        with self.assertRaises(ValueError):
            make_app(self.store,{"a":self.game,"b":self.game},self.admin)

    def test_migration(self):
        p=Path(self.tmp.name)/"old.sqlite3"
        with sqlite3.connect(p) as db:
            db.executescript("CREATE TABLE sessions(token_hash BLOB PRIMARY KEY,game_session TEXT UNIQUE,expires REAL,seq TEXT,last_seen REAL); CREATE TABLE events(id INTEGER PRIMARY KEY,created REAL,game_session TEXT,kind TEXT,source TEXT); INSERT INTO events VALUES(1,100,'s','module_unlisted','client_unverified');")
        migrated=Store(p)
        self.assertEqual(migrated.overview()["events"][0]["server_id"],"default")
        self.assertTrue(migrated.issue("same","vip"))
        self.assertTrue(migrated.issue("same","normal"))
