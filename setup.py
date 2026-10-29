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

# Fork of microsoft/playwright-python that runs the driver with the system's bun
# (see FORK.md). Upstream builds one wheel per platform because it bundles the
# Node.js binary; the driver itself (the playwright-core npm package) is plain
# JavaScript, so this builds a single py3-none-any wheel with scripts/fetch_driver.py.

import os
import sys
from pathlib import Path

from setuptools import setup

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_driver  # noqa: E402
import fork_version  # noqa: E402

# The tree is a merge of an upstream tag plus fork commits, so setuptools-scm
# would report a dev version; pin it to <upstream>+bun.<revision> instead.
os.environ.setdefault("SETUPTOOLS_SCM_PRETEND_VERSION", fork_version.fork_version())

# Metadata-only invocations (egg_info, dist_info, sdist) don't need the driver.
if {"bdist_wheel", "build", "build_py", "develop", "editable_wheel", "install"} & set(
    sys.argv
):
    fetch_driver.fetch((ROOT / "DRIVER_VERSION").read_text().strip())

setup(package_data={"playwright": ["driver/**/*"]})
