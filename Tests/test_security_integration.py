"""Local defensive regression and concurrency tests; no public targets."""
import concurrent.futures
import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler
from Server.service import Store, make_app
from Server.registry import load_registry

class Quiet(WSGIRequestHandler):
    def log_message(self, *args):
        pass

class SecurityIntegration(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"db.sqlite3"
        self.store=Store(self.path)
        self.keys={"normal":"a"*64,"vip":"b"*64}
        self.admin="c"*64
        self.app=make_app(self.store,self.keys,self.admin)

    def request(self,path,key,raw,method="POST"):
        result=[]
        body=b"".join(self.app({"REQUEST_METHOD":method,"PATH_INFO":path,
            "HTTP_AUTHORIZATION":"Bearer "+key,"CONTENT_TYPE":"application/json",
            "CONTENT_LENGTH":str(len(raw)),"wsgi.input":io.BytesIO(raw)},
            lambda status,headers:result.append(int(status.split()[0]))))
        return result[0],body

    def test_strict_json(self):
        path="/v1/session/issue"
        for raw in (b'{"game_session":"one","game_session":"two"}',
                    b'{"game_session":NaN}',b'{"game_session":"\xff"}',
                    b'['*1500+b']'*1500):
            self.assertEqual(self.request(path,self.keys["normal"],raw)[0],400)
        self.assertEqual(self.request(path,"x"*4096,b'{}')[0],401)
        self.assertEqual(self.request(path,self.keys["normal"],b' '*4097)[0],413)

    def test_concurrent_replay(self):
        token=self.store.issue("player","normal")
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:self.store.accept(token,1,"memory_mismatch"),range(16)))
        self.assertEqual(sum(results),1)
        self.assertEqual(len(self.store.overview()["events"]),1)

    def test_concurrent_rotation(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            tokens=list(pool.map(lambda _:self.store.issue("same","normal"),range(12)))
        self.assertEqual(sum(self.store.accept(t,1) for t in tokens),1)

    def test_removed_server_cannot_revive(self):
        token=self.store.issue("player","vip")
        make_app(self.store,{"normal":self.keys["normal"]},self.admin)
        make_app(self.store,self.keys,self.admin)
        self.assertFalse(self.store.accept(token,1))

    def test_registry_strict(self):
        p=self.path.parent/"registry.xml"
        for xml in ('<ShieldServers version="1"/>',
                    '<ShieldServers version="1"><Server id="a" keyEnv="SHIELD_GAME_KEY_A">text</Server></ShieldServers>',
                    '<ShieldServers version="1"><Server id="a" keyEnv="SHIELD_GAME_KEY_A"/><Server id="b" keyEnv="SHIELD_GAME_KEY_A"/></ShieldServers>',
                    '<!DOCTYPE x><ShieldServers version="1"/>'):
            p.write_text(xml,encoding="utf-8")
            with self.assertRaises(ValueError):
                load_registry({"SHIELD_REGISTRY":str(p),"SHIELD_GAME_KEY_A":"a"*64})

    def test_loopback_lifecycle(self):
        # Real HTTP socket on ephemeral loopback port, not a TLS or MU runtime test.
        with make_server("127.0.0.1",0,self.app,handler_class=Quiet) as server:
            worker=threading.Thread(target=server.serve_forever,daemon=True)
            worker.start()
            def call(path,key,obj=None):
                conn=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=5)
                try:
                    conn.request("GET" if obj is None else "POST",path,
                        body=None if obj is None else json.dumps(obj),
                        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
                    response=conn.getresponse()
                    return response.status,response.read()
                finally:
                    conn.close()
            try:
                code,raw=call("/v1/session/issue",self.keys["normal"],{"game_session":"same"})
                self.assertEqual(code,201)
                token=json.loads(raw)["token"]
                self.assertEqual(call("/v1/heartbeat",token,{"sequence":1})[0],204)
                self.assertEqual(call("/v1/events",token,{"sequence":2,"kind":"module_unlisted"})[0],204)
                self.assertEqual(call("/v1/admin/sessions",token)[0],401)
                code,raw=call("/v1/admin/sessions",self.admin)
                self.assertEqual(code,200)
                self.assertNotIn(token.encode(),raw)
                self.assertEqual(json.loads(raw)["sessions"][0]["server_id"],"normal")
                self.assertEqual(call("/v1/session/revoke",self.keys["vip"],{"game_session":"same"})[0],204)
                self.assertEqual(call("/v1/heartbeat",token,{"sequence":3})[0],204)
                self.assertEqual(call("/v1/session/revoke",self.keys["normal"],{"game_session":"same"})[0],204)
                self.assertEqual(call("/v1/heartbeat",token,{"sequence":4})[0],401)
            finally:
                server.shutdown()
                worker.join(5)
