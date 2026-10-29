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

import inspect
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple

import playwright
from playwright._impl._errors import Error
from playwright._repo_version import version


def find_bun() -> Optional[str]:
    # PLAYWRIGHT_NODEJS_PATH is honoured for compatibility with upstream.
    for var in ("PLAYWRIGHT_BUN_PATH", "PLAYWRIGHT_NODEJS_PATH"):
        if os.getenv(var):
            return os.environ[var]
    on_path = shutil.which("bun")
    if on_path:
        return on_path
    # The bun installer puts the binary in $BUN_INSTALL/bin (default ~/.bun/bin)
    # and only adds it to PATH of interactive shells.
    bun_home = Path(os.getenv("BUN_INSTALL") or Path.home() / ".bun")
    candidate = bun_home / "bin" / ("bun.exe" if sys.platform == "win32" else "bun")
    return str(candidate) if candidate.is_file() else None


def compute_driver_executable() -> Tuple[str, str]:
    driver_path = Path(inspect.getfile(playwright)).parent / "driver"
    cli_path = str(driver_path / "package" / "cli.js")
    bun = find_bun()
    if not bun:
        raise Error(
            "bun was not found. This build of Playwright runs its driver with bun "
            "instead of a bundled Node.js: install bun (https://bun.sh) and put it "
            "on PATH, or set PLAYWRIGHT_BUN_PATH to the bun executable."
        )
    return (bun, cli_path)


def get_driver_env() -> dict:
    env = os.environ.copy()
    env["PW_LANG_NAME"] = "python"
    env["PW_LANG_NAME_VERSION"] = f"{sys.version_info.major}.{sys.version_info.minor}"
    env["PW_CLI_DISPLAY_VERSION"] = version
    return env
