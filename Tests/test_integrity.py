import pathlib
import subprocess
import tempfile
import unittest
from Tools.integrity import manifest, verify, safe_file

class IntegrityTests(unittest.TestCase):
    def test_signed_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            root = base / "client"
            root.mkdir()
            target = root / "main.exe"
            target.write_bytes(b"test fixture")
            raw = manifest(root, ["main.exe"])
            data = base / "manifest.json"
            data.write_bytes(raw)
            key, pub, sig = (base / n for n in ("private.pem", "public.pem", "manifest.sig"))
            def openssl(*args):
                subprocess.run(["openssl", *map(str, args)], check=True, capture_output=True)
            openssl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", key)
            openssl("pkey", "-in", key, "-pubout", "-out", pub)
            openssl("dgst", "-sha256", "-sign", key, "-out", sig, data)
            signature = sig.read_bytes()
            self.assertEqual(verify(root, raw, signature, pub), [])
            with self.assertRaises(ValueError):
                verify(root, raw+b" ", signature, pub)
            target.write_bytes(b"modified")
            self.assertEqual(verify(root, raw, signature, pub), [("main.exe", "modified")])
            target.unlink()
            self.assertEqual(len(verify(root, raw, signature, pub)), 1)
            with self.assertRaises(ValueError):
                safe_file(root, "../private.pem")
            with self.assertRaises(ValueError):
                manifest(root, ["main.exe", "MAIN.EXE"])

if __name__ == "__main__":
    unittest.main()
