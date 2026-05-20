#!/usr/bin/env python3
"""Set the source package version using PEP 440 normalization."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from packaging.version import Version
except ModuleNotFoundError:
    from pip._vendor.packaging.version import Version


VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$')


def read_version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        match = VERSION_PATTERN.match(line)
        if match:
            return match.group(1)
    raise SystemExit(f"Unable to find __version__ in {path}")


def write_version(path: Path, version: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, line in enumerate(lines):
        if VERSION_PATTERN.match(line.strip()):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f'__version__ = "{version}"{newline}'
            path.write_text("".join(lines), encoding="utf-8")
            return
    raise SystemExit(f"Unable to find __version__ in {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", nargs="?")
    parser.add_argument("--path", default="src/kop/__init__.py")
    args = parser.parse_args()

    version_path = Path(args.path)
    if args.version:
        write_version(version_path, str(Version(args.version)))

    print(read_version(version_path))


if __name__ == "__main__":
    main()
