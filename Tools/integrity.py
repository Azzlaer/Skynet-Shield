"""Offline client integrity tooling. Requires Python 3.9+ and OpenSSL."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

def safe_file(root, name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", name):
        raise ValueError("Invalid relative path")
    parts = name.split("/")
    if any(p in (".", "..") or p.endswith(".") or p.split(".")[0].upper() in
           {"CON", "PRN", "AUX", "NUL", *("COM"+str(i) for i in range(1,10)), *("LPT"+str(i) for i in range(1,10))} for p in parts):
        raise ValueError("Unsafe path")
    root = root.resolve(strict=True)
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Symlinks are not supported")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("Not a regular file within client root")
    return resolved

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()

def manifest(root, names):
    if not names or len({n.casefold() for n in names}) != len(names):
        raise ValueError("Empty or duplicate file list")
    return (json.dumps({"version": 1, "files": [
        {"path": n, "sha256": sha256(safe_file(root, n))} for n in sorted(names)
    ]}, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def verify(root, raw, signature, public_key):
    # Verify precisely the bytes subsequently parsed, not a mutable source file.
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp)/"manifest"
        sig = Path(tmp)/"signature"
        data.write_bytes(raw)
        sig.write_bytes(signature)
        result = subprocess.run(["openssl", "dgst", "-sha256", "-verify",
                                 str(public_key.resolve(strict=True)), "-signature",
                                 str(sig), str(data)], capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError("Invalid manifest signature")
    doc = json.loads(raw)
    if not isinstance(doc, dict) or set(doc) != {"version", "files"} or type(doc["version"]) is not int or doc["version"] != 1:
        raise ValueError("Unsupported manifest")
    entries = doc["files"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("Empty or invalid file list")
    seen = set()
    failures = []
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("Invalid entry")
        name, expected = item["path"], item["sha256"]
        if not isinstance(name, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid path or hash")
        if name.casefold() in seen:
            raise ValueError("Duplicate path")
        seen.add(name.casefold())
        try:
            if sha256(safe_file(root, name)) != expected:
                failures.append((name, "modified"))
        except (OSError, ValueError):
            failures.append((name, "missing, unreadable or unsafe"))
    return failures

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("root", type=Path)
    create.add_argument("output", type=Path)
    create.add_argument("files", nargs="+")
    check = sub.add_parser("verify")
    for arg in ("root", "manifest", "signature", "public_key"):
        check.add_argument(arg, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "create":
            args.output.write_bytes(manifest(args.root, args.files))
            return 0
        failures = verify(args.root, args.manifest.read_bytes(), args.signature.read_bytes(), args.public_key)
        for name, reason in failures:
            print(f"{name!r}: {reason}")
        if not failures:
            print("All listed files verified")
        return 1 if failures else 0
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(f"Integrity check failed: {exc}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
