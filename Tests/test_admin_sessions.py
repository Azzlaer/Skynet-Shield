import io
import json
import tempfile
import unittest
from pathlib import Path
from Server.service import Store, make_app

class AdminSessionsTests(unittest.TestCase):
    def test_scope_and_privacy(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/"db.sqlite3",clock=lambda:100)
            token=store.issue("same","normal")
            store.issue("same","vip")
            store.issue("hidden","removed")
            store.accept(token,1)
            app=make_app(store,{"normal":"a"*64,"vip":"c"*64},"b"*64)
            def get(path,key):
                status=[]
                raw=b"".join(app({"REQUEST_METHOD":"GET","PATH_INFO":path,"HTTP_AUTHORIZATION":"Bearer "+key,"wsgi.input":io.BytesIO()},lambda s,h:status.append(int(s.split()[0]))))
                return status[0],json.loads(raw) if raw else None
            self.assertEqual(get("/v1/admin/sessions","a"*64)[0],401)
            code,data=get("/v1/admin/sessions","b"*64)
            self.assertEqual(code,200)
            self.assertEqual({r["server_id"] for r in data["sessions"]},{"normal","vip"})
            self.assertEqual(set(data["sessions"][0]),{"server_id","game_session","expires","last_seen"})
            self.assertEqual(get("/v1/admin/overview","b"*64)[1]["active_sessions"],2)
            self.assertFalse(data["truncated"])

    def test_limit(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/"db.sqlite3")
            for i in range(501): store.issue("s"+str(i))
            app=make_app(store,"a"*64,"b"*64)
            status=[]
            body=b"".join(app({"REQUEST_METHOD":"GET","PATH_INFO":"/v1/admin/sessions","HTTP_AUTHORIZATION":"Bearer "+"b"*64},lambda s,h:status.append(s)))
            data=json.loads(body)
            self.assertTrue(data["truncated"])
            self.assertEqual(len(data["sessions"]),500)
