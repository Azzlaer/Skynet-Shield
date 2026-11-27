import io
import json
import tempfile
import unittest
from pathlib import Path
from Server.service import Store, make_app

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"db.sqlite3"
        self.now = [100]
        self.store = Store(self.path, ttl=10, clock=lambda:self.now[0])
        self.game, self.admin = "a"*64, "b"*64
        self.app = make_app(self.store,self.game,self.admin)

    def request(self,path,token,obj=None,method="POST"):
        data = json.dumps(obj).encode() if obj is not None else b""
        env = {"REQUEST_METHOD":method,"PATH_INFO":path,"HTTP_AUTHORIZATION":"Bearer "+token,
               "CONTENT_TYPE":"application/json","CONTENT_LENGTH":str(len(data)),"wsgi.input":io.BytesIO(data)}
        status=[]
        body=b"".join(self.app(env,lambda s,h:status.append(int(s.split()[0]))))
        return status[0],json.loads(body) if body else None

    def test_lifecycle(self):
        issue="/v1/session/issue"
        self.assertEqual(self.request(issue,self.admin,{"game_session":"s1"})[0],401)
        code,data=self.request(issue,self.game,{"game_session":"s1"})
        self.assertEqual(code,201)
        token=data["token"]
        self.assertEqual(self.request("/v1/heartbeat",token,{"sequence":1})[0],204)
        self.assertEqual(self.request("/v1/heartbeat",token,{"sequence":1})[0],401)
        self.assertEqual(self.request("/v1/events",token,{"sequence":2,"kind":"memory_mismatch"})[0],204)
        self.assertEqual(self.request("/v1/events",token,{"sequence":3,"kind":None})[0],400)
        self.assertEqual(self.request("/v1/admin/overview",token,method="GET")[0],401)
        code,overview=self.request("/v1/admin/overview",self.admin,method="GET")
        self.assertEqual(code,200)
        self.assertEqual(overview["active_sessions"],1)
        self.assertEqual(overview["events"][0]["source"],"client_unverified")
        reopened=Store(self.path,clock=lambda:self.now[0])
        self.assertFalse(reopened.accept(token,2))
        self.assertTrue(reopened.accept(token,3))
        self.now[0]=110
        self.assertFalse(reopened.accept(token,4))

    def test_rotation_revoke(self):
        first=self.store.issue("s1")
        second=self.store.issue("s1")
        self.assertFalse(self.store.accept(first,1))
        self.assertTrue(self.store.accept(second,1))
        self.store.revoke("s1")
        self.assertFalse(self.store.accept(second,2))

    def test_keys(self):
        with self.assertRaises(ValueError):
            make_app(self.store,self.game,self.game)
