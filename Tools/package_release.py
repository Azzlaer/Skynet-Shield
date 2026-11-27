"""Build an allowlisted alpha distribution from successful Windows builds."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile
import zipfile

VERSION = "1.0.0-alpha"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "README.md","CHANGELOG.md","SECURITY.md",
    "Server/action_patterns.py","Server/registry.py","Server/run.py","Server/service.py","Server/session.py",
    "Config/ShieldServers.example.xml","Tools/integrity.py",
    "Integration/Client/SessionWorker.cpp","Integration/Client/SessionWorker.h",
    "Integration/GameServer/shield_api.py",
    "Common/Shield.h","Common/MemoryGuard.h","Common/ProcessMonitor.h","Common/SecureCommunication.h",
    "Bridge/ShieldBridge.h",
    "Docs/AdminCP-V2.md","Docs/AdminCP.md","Docs/AntiMacro.md","Docs/Architecture.md",
    "Docs/Integrity.md","Docs/MUIntegration.md","Docs/MemoryGuard.md","Docs/MultiGameServer.md",
    "Docs/ProcessMonitor.md","Docs/SecureCommunication.md","Docs/SecurityReview.md",
    "Docs/ShieldBridge.md","Docs/ShieldServer.md","Docs/Installation.es.md",
    "Deployment/Check-Prerequisites.ps1","Deployment/Start-LocalShield.ps1",
)
NATIVE = ("SkynetShield.dll","SkynetShield.lib","ShieldBridge.dll","ShieldBridge.lib")
ADMIN = ("SkynetShield.Admin.exe","SkynetShield.Admin.dll",
         "SkynetShield.Admin.deps.json","SkynetShield.Admin.runtimeconfig.json")

def copy(source, target):
    if not source.is_file() or source.is_symlink():
        raise ValueError("Missing or unsafe input: "+str(source))
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def package(root, x86, x64, admin, out):
    out.mkdir(parents=True,exist_ok=True)
    name="SkynetShield-"+VERSION+"-windows"
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp)/name
        for rel in SOURCE:
            copy(root/rel,stage/rel)
        for arch,source in (("x86",x86),("x64",x64)):
            for filename in NATIVE:
                copy(source/filename,stage/"Native"/arch/filename)
        for filename in ADMIN:
            copy(admin/filename,stage/"AdminCP"/filename)
        entries=sorted(p for p in stage.rglob("*") if p.is_file())
        manifest="".join(digest(p)+"  "+p.relative_to(stage).as_posix()+"\n" for p in entries)
        (stage/"SHA256SUMS.txt").write_text(manifest,encoding="utf-8",newline="\n")
        archive=out/(name+".zip")
        # Create in destination directory and replace only after successful writing.
        with tempfile.TemporaryDirectory(dir=out) as scratch:
            temp=Path(scratch)/archive.name
            with zipfile.ZipFile(temp,"w",zipfile.ZIP_DEFLATED) as z:
                for p in sorted(stage.rglob("*")):
                    if p.is_file():
                        z.write(p,Path(name)/p.relative_to(stage))
            temp.replace(archive)
        (out/(archive.name+".sha256")).write_text(digest(archive)+"  "+archive.name+"\n",encoding="ascii",newline="\n")
        return archive

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for arg in ("x86","x64","admin","out"):
        parser.add_argument("--"+arg,type=Path,required=True)
    args=parser.parse_args()
    print(package(ROOT,args.x86,args.x64,args.admin,args.out))
