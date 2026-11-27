"""Server-only registry. XML contains environment variable names, never keys."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
HEX = re.compile(r"[0-9a-f]{64}")
ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
ENV = re.compile(r"SHIELD_GAME_KEY(?:_[A-Z0-9_]+)?")

def validate_registry(registry, admin):
    if not isinstance(registry,dict) or not 1 <= len(registry) <= 128 or not isinstance(admin,str) or not HEX.fullmatch(admin):
        raise ValueError("Invalid registry")
    seen = {admin}
    for sid,key in registry.items():
        if not isinstance(sid,str) or not ID.fullmatch(sid) or not isinstance(key,str) or not HEX.fullmatch(key) or key in seen:
            raise ValueError("Invalid or duplicate server credential")
        seen.add(key)
    return dict(registry)

def load_registry(env):
    if not env.get("SHIELD_REGISTRY"):
        return {"default":env["SHIELD_GAME_KEY"]}
    with Path(env["SHIELD_REGISTRY"]).open("rb") as stream:
        data=stream.read(32769)
    if len(data)>32768 or b"<!" in data or b"\x00" in data:
        raise ValueError("Unsupported registry XML")
    try:
        root=ET.fromstring(data.decode("utf-8"))
    except (ET.ParseError, UnicodeError) as exc:
        raise ValueError("Invalid registry XML") from exc
    if root.tag!="ShieldServers" or root.attrib!={"version":"1"}:
        raise ValueError("Invalid registry XML")
    if not 1 <= len(root) <= 128 or (root.text or "").strip():
        raise ValueError("Invalid registry size or text")
    result={}
    names=set()
    for entry in root:
        if entry.tag!="Server" or set(entry.attrib)!={"id","keyEnv"} or len(entry) or (entry.text or "").strip() or (entry.tail or "").strip():
            raise ValueError("Invalid server entry")
        sid,name=entry.attrib["id"],entry.attrib["keyEnv"]
        if sid in result or name in names or not ID.fullmatch(sid) or not ENV.fullmatch(name):
            raise ValueError("Invalid server entry")
        names.add(name)
        result[sid]=env[name]
    return result
