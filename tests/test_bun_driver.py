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

import os
import subprocess
from pathlib import Path

import pytest

from playwright._impl._driver import compute_driver_executable, find_bun
from playwright._impl._errors import Error


@pytest.fixture
def no_bun_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    for var in ("PLAYWRIGHT_BUN_PATH", "PLAYWRIGHT_NODEJS_PATH", "BUN_INSTALL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def _fake_bun(directory: Path) -> Path:
    name = "bun.exe" if os.name == "nt" else "bun"
    path = directory / name
    path.write_text("")
    path.chmod(0o755)
    return path


def test_bun_on_path_is_used(no_bun_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bun = _fake_bun(no_bun_env)
    monkeypatch.setenv("PATH", str(no_bun_env))
    executable, cli = compute_driver_executable()
    assert Path(executable).resolve() == bun.resolve()
    assert Path(cli).name == "cli.js"
    assert Path(cli).parent.name == "package"


def test_explicit_path_wins_over_path_lookup(
    no_bun_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_bun(no_bun_env)
    monkeypatch.setenv("PLAYWRIGHT_BUN_PATH", "/custom/bun")
    assert find_bun() == "/custom/bun"


def test_upstream_nodejs_path_env_still_honoured(
    no_bun_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PLAYWRIGHT_NODEJS_PATH", "/custom/runtime")
    assert find_bun() == "/custom/runtime"


def test_bun_install_dir_is_searched(
    no_bun_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = no_bun_env / "bun-home" / "bin"
    bin_dir.mkdir(parents=True)
    bun = _fake_bun(bin_dir)
    monkeypatch.setenv("BUN_INSTALL", str(no_bun_env / "bun-home"))
    assert find_bun() == str(bun)


def test_default_bun_install_dir_is_searched(no_bun_env: Path) -> None:
    bin_dir = no_bun_env / ".bun" / "bin"
    bin_dir.mkdir(parents=True)
    bun = _fake_bun(bin_dir)
    assert find_bun() == str(bun)


def test_missing_bun_raises_helpful_error(no_bun_env: Path) -> None:
    with pytest.raises(Error, match="PLAYWRIGHT_BUN_PATH"):
        compute_driver_executable()


def test_driver_cli_runs_under_bun() -> None:
    executable, cli = compute_driver_executable()
    result = subprocess.run(
        [executable, cli, "--version"], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip().startswith("Version ")
