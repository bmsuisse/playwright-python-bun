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

"""Version of this fork, derived from the files the sync script maintains.

UPSTREAM_TAG      the upstream release the tree is based on, e.g. ``v1.64.1``
FORK_REVISION     bumped by hand when the fork's own patch changes; reset to 1
                  by scripts/sync_upstream.py on every upstream release

``python scripts/fork_version.py``        -> ``1.64.1.post1`` (Python version)
``python scripts/fork_version.py --tag``  -> ``v1.64.1-bun.1`` (git tag)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text().strip()


def upstream_version() -> str:
    return _read("UPSTREAM_TAG").removeprefix("v")


def fork_version() -> str:
    # A post release, not a local version (+bun.1): PyPI rejects local versions.
    return f"{upstream_version()}.post{_read('FORK_REVISION')}"


def fork_tag() -> str:
    return f"v{upstream_version()}-bun.{_read('FORK_REVISION')}"


if __name__ == "__main__":
    print(fork_tag() if "--tag" in sys.argv[1:] else fork_version())
