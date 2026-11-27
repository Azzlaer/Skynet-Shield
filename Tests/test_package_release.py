import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from Tools.package_release import package,SOURCE,NATIVE,ADMIN

class PackageTests(unittest.TestCase):
    def test_allowlist_and_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            root=base/"root"
            for rel in SOURCE:
                p=root/rel
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(rel.encode())
            for folder,names in (("x86",NATIVE),("x64",NATIVE),("admin",ADMIN)):
                path=base/folder
                path.mkdir()
                for name in names:
                    (path/name).write_bytes(name.encode())
                (path/"secret.key").write_text("private")
            (root/"shield.sqlite3").write_bytes(b"private")
            out=base/"out"
            archive=package(root,base/"x86",base/"x64",base/"admin",out)
            with zipfile.ZipFile(archive) as z:
                names=z.namelist()
                self.assertEqual(len(names),len(SOURCE)+2*len(NATIVE)+len(ADMIN)+1)
                self.assertFalse(any("secret.key" in n or ".sqlite3" in n for n in names))
                prefix=names[0].split("/")[0]+"/"
                manifest=z.read(prefix+"SHA256SUMS.txt").decode()
                for line in manifest.splitlines():
                    digest,rel=line.split("  ",1)
                    self.assertEqual(hashlib.sha256(z.read(prefix+rel)).hexdigest(),digest)
            expected=(out/(archive.name+".sha256")).read_text().split()[0]
            self.assertEqual(expected,hashlib.sha256(archive.read_bytes()).hexdigest())
            (base/"x86"/NATIVE[0]).unlink()
            with self.assertRaises(ValueError):
                package(root,base/"x86",base/"x64",base/"admin",out)
