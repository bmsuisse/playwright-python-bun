#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Fetch the Playwright driver (the ``playwright-core`` npm package).

Fork replacement for ``build_driver.py``: no Node.js binary is bundled (the
driver is started with the system's bun), so there is nothing platform
specific and the package is unpacked straight into ``playwright/driver/package``.
Needs only the Python standard library, no npm.

The tarball is downloaded from the npm registry and checked against the
integrity hash the registry reports for it.
"""

import base64
import hashlib
import io
import json
import shutil
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER_DIR = REPO_ROOT / "playwright" / "driver"
REGISTRY = "https://registry.npmjs.org"


def _read(url: str) -> bytes:
    last_error: Exception = RuntimeError("no attempt made")
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(url) as response:  # noqa: S310
                return response.read()
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"  attempt {attempt} failed: {error}", file=sys.stderr)
            time.sleep(attempt)
    raise SystemExit(f"Failed to download {url}: {last_error}")


def _verify(data: bytes, integrity: str) -> None:
    algorithm, _, expected = integrity.partition("-")
    digest = base64.b64encode(hashlib.new(algorithm, data).digest()).decode()
    if digest != expected:
        raise SystemExit(f"Integrity check failed for playwright-core: {integrity}")


def _extract(tar: tarfile.TarFile, destination: Path) -> None:
    # npm tarballs nest every file under a top-level "package/" directory,
    # which is exactly the layout the Python client expects.
    members = [m for m in tar.getmembers() if m.name.startswith("package/")]
    if not members:
        raise SystemExit("No package/ entries found in the playwright-core tarball")
    if hasattr(tarfile, "data_filter"):
        tar.extractall(destination, members=members, filter="data")
    else:
        for member in members:
            if member.name.startswith(("/", "..")) or ".." in Path(member.name).parts:
                raise SystemExit(f"Unsafe path in tarball: {member.name}")
        tar.extractall(destination, members=members)  # noqa: S202


def fetch(version: str, destination: Path = DRIVER_DIR) -> None:
    marker = destination / ".driver-version"
    if marker.is_file() and marker.read_text() == version:
        return
    print(f"Fetching playwright-core@{version}", flush=True)
    metadata = json.loads(_read(f"{REGISTRY}/playwright-core/{version}"))
    tarball = _read(metadata["dist"]["tarball"])
    _verify(tarball, metadata["dist"]["integrity"])
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
        _extract(tar, destination)
    marker.write_text(version)
    print(f"Driver unpacked to {destination / 'package'}")


def main() -> None:
    fetch((REPO_ROOT / "DRIVER_VERSION").read_text().strip())


if __name__ == "__main__":
    main()
