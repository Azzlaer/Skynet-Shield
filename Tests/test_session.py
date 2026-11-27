import unittest
from concurrent.futures import ThreadPoolExecutor
from Server.session import SessionStore

class SessionTests(unittest.TestCase):
    def test_replay_expiration_revocation(self):
        now = [0]
        store = SessionStore(ttl=10, clock=lambda: now[0])
        token = store.issue()
        self.assertFalse(store.heartbeat(token, True))
        self.assertFalse(store.heartbeat(token, 0))
        self.assertFalse(store.heartbeat("a"*64, 1))
        self.assertTrue(store.heartbeat(token, 1))
        self.assertFalse(store.heartbeat(token, 1))
        self.assertTrue(store.heartbeat(token, 3))
        self.assertFalse(store.heartbeat(token, 2))
        now[0] = 10
        self.assertFalse(store.heartbeat(token, 4))
        token = store.issue()
        store.revoke(token)
        self.assertFalse(store.heartbeat(token, 1))

    def test_concurrent_replay(self):
        store = SessionStore()
        token = store.issue()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: store.heartbeat(token, 1), range(20)))
        self.assertEqual(sum(results), 1)

    def test_capacity(self):
        store = SessionStore(capacity=1)
        store.issue()
        with self.assertRaises(RuntimeError):
            store.issue()
