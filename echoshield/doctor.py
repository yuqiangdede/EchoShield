from __future__ import annotations

import platform
import shutil
import subprocess
import sys


def _version(tool: str) -> str | None:
    path = shutil.which(tool)
    if not path:
        return None
    proc = subprocess.run([tool, "-version"], text=True, capture_output=True)
    line = (proc.stdout or proc.stderr).splitlines()
    return line[0] if line else path


def main() -> int:
    rows = [
        ("Python", sys.version.split()[0], sys.version_info >= (3, 10)),
        ("Platform", platform.platform(), True),
    ]
    for tool in ("ffmpeg", "ffprobe"):
        version = _version(tool)
        rows.append((tool, version or "NOT FOUND", version is not None))

    try:
        import numpy as np
        rows.append(("numpy", np.__version__, True))
    except Exception as exc:
        rows.append(("numpy", f"ERROR: {exc}", False))

    print("EchoShield environment check")
    print("-" * 72)
    ok = True
    for name, value, passed in rows:
        mark = "OK" if passed else "FAIL"
        print(f"[{mark:4}] {name:10} {value}")
        ok = ok and passed
    if not ok:
        print("\nFix failed items, then run echoshield-doctor again.")
        return 1
    print("\nEnvironment is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
