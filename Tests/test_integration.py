import unittest
from unittest.mock import patch
from Integration.GameServer.shield_api import ShieldApi

class AdapterTests(unittest.TestCase):
    def test_reject_plain_http(self):
        with self.assertRaises(ValueError):
            ShieldApi("http://example.test","a"*64)

    def test_grant_and_logout(self):
        api=ShieldApi("https://example.test","a"*64)
        with patch.object(api,"_post",return_value=(201,b'{"token":"'+b'b'*64+b'","expires_in":300}')) as post:
            grant=api.issue_after_authenticated_login("opaque1")
            self.assertEqual(grant.token,"b"*64)
            self.assertEqual(grant.expires_in,300)
            post.assert_called_once_with("/v1/session/issue","opaque1")
        with patch.object(api,"_post",return_value=(204,b"")) as post:
            api.revoke_on_logout("opaque1")
            post.assert_called_once_with("/v1/session/revoke","opaque1")

    def test_invalid_grant(self):
        api=ShieldApi("https://example.test","a"*64)
        with patch.object(api,"_post",return_value=(201,b'{"token":"bad","expires_in":300}')):
            with self.assertRaises(ValueError):
                api.issue_after_authenticated_login("opaque1")
