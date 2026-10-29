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

"""Merge the newest upstream release tag into this fork.

Run from the fork's repository root with a clean working tree. If upstream has
a stable release (``vX.Y.Z``) newer than ``UPSTREAM_TAG``, this merges that tag,
bumps ``UPSTREAM_TAG``, resets ``FORK_REVISION`` to 1 and commits. It never
pushes. Exit codes: 0 up to date or merged, 1 the merge needs a human.

The fork only owns a handful of files (see FORK.md), so a merge normally is
clean. Two things are resolved here instead of by hand, because they would
conflict on every release:

* upstream's GitHub workflows are not used by the fork (they publish to PyPI
  with upstream's identity), so every workflow not named ``bun-*.yml`` is
  removed again after the merge;
* ``UPSTREAM_TAG`` and ``FORK_REVISION`` are rewritten.

Anything else that conflicts (typically setup.py or _driver.py when upstream
touched them) aborts the merge and lists the files.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

UPSTREAM_URL = "https://github.com/microsoft/playwright-python.git"
REPO_ROOT = Path(__file__).resolve().parent.parent
STABLE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
WORKFLOW_DIR = ".github/workflows"
FORK_WORKFLOW_PREFIX = "bun-"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=check, capture_output=True, text=True
    )


def parse(tag: str) -> Optional[Tuple[int, int, int]]:
    match = STABLE_TAG.match(tag)
    return (int(match[1]), int(match[2]), int(match[3])) if match else None


def latest_upstream_tag() -> str:
    if git("remote", "get-url", "upstream", check=False).returncode != 0:
        git("remote", "add", "upstream", UPSTREAM_URL)
    git("fetch", "--quiet", "upstream", "--tags")
    tags = [t for t in git("tag", "--list", "v*").stdout.split() if parse(t)]
    return max(tags, key=lambda t: parse(t) or (0, 0, 0))


def is_fork_workflow(path: str) -> bool:
    return not path.startswith(f"{WORKFLOW_DIR}/") or Path(path).name.startswith(
        FORK_WORKFLOW_PREFIX
    )


def drop_upstream_workflows() -> None:
    tracked = git("ls-files", WORKFLOW_DIR).stdout.split()
    stale = [p for p in tracked if not is_fork_workflow(p)]
    if stale:
        git("rm", "--quiet", "--force", "--", *stale)


def unresolved_conflicts() -> List[str]:
    unmerged = git("diff", "--name-only", "--diff-filter=U").stdout.split()
    for path in [p for p in unmerged if not is_fork_workflow(p)]:
        git("rm", "--quiet", "--force", "--", path)
    return [p for p in unmerged if is_fork_workflow(p)]


def set_output(**values: str) -> None:
    for key, value in values.items():
        print(f"{key}={value}")
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as file:
            file.writelines(f"{key}={value}\n" for key, value in values.items())


def main() -> int:
    if git("status", "--porcelain").stdout.strip():
        print("Working tree is not clean", file=sys.stderr)
        return 1
    current = (REPO_ROOT / "UPSTREAM_TAG").read_text().strip()
    latest = latest_upstream_tag()
    if (parse(latest) or (0, 0, 0)) <= (parse(current) or (0, 0, 0)):
        print(f"Up to date with upstream {current}")
        set_output(updated="false", tag=current)
        return 0

    print(f"Merging upstream {latest} (fork is on {current})")
    merge = git("merge", "--no-ff", "--no-commit", latest, check=False)
    conflicts = unresolved_conflicts() if merge.returncode else []
    if conflicts:
        git("merge", "--abort")
        print(f"Merge of {latest} needs manual resolution:", file=sys.stderr)
        print("\n".join(f"  {path}" for path in conflicts), file=sys.stderr)
        return 1
    if (
        merge.returncode
        and not git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).stdout
    ):
        print(merge.stdout + merge.stderr, file=sys.stderr)
        return 1

    drop_upstream_workflows()
    (REPO_ROOT / "UPSTREAM_TAG").write_text(f"{latest}\n")
    (REPO_ROOT / "FORK_REVISION").write_text("1\n")
    git("add", "UPSTREAM_TAG", "FORK_REVISION")
    git("commit", "--quiet", "-m", f"chore: merge upstream {latest}")
    set_output(updated="true", tag=latest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
