# Playwright for Python, driven by bun

A fork of [microsoft/playwright-python](https://github.com/microsoft/playwright-python)
that runs the Playwright driver with the system's [bun](https://bun.sh) instead of a
bundled Node.js binary.

**Scope: headless browsers in CI.** That is what is tested, on Linux. Headed mode is
untested (CI has no display), and macOS, Windows, Firefox and WebKit are not in the test
matrix. The driver code is the same, so they are expected to work, but nothing checks it.

Upstream has no such distribution: `playwright-python` only ships wheels that bundle
Node.js, and its maintainers have said there are
[no plans](https://github.com/microsoft/playwright-python/issues/3036) for one that uses
a system runtime. Linux distributions repackage it against a system Node.js, nothing we
found does the same for bun.

|                | upstream wheel              | this fork                  |
| -------------- | --------------------------- | -------------------------- |
| Wheels         | one per OS/CPU (~45 MB each) | one `py3-none-any` (~3.7 MB) |
| Driver runtime | Node.js, bundled            | bun, from `PATH`           |
| Version        | `1.64.1`                    | `1.64.1+bun.1`             |

The Python API is untouched: `import playwright` works exactly as before. The driver is
the same `playwright-core` npm package as upstream, run as `bun cli.js`.

## Use it

Requires [bun](https://bun.sh) on `PATH`. The runtime is looked up in this order:
`PLAYWRIGHT_BUN_PATH`, `PLAYWRIGHT_NODEJS_PATH` (kept for upstream compatibility),
`bun` on `PATH`, `$BUN_INSTALL/bin/bun` (default `~/.bun/bin/bun`). If none is found the
first call raises an error that says so.

With uv, as a drop-in replacement for the `playwright` distribution (this also satisfies
`pytest-playwright` and other packages that depend on `playwright`):

```toml
# pyproject.toml
[tool.uv.sources]
playwright = { git = "https://github.com/bmsuisse/playwright-python-bun", tag = "v1.64.1-bun.1" }
```

or with pip: `pip install "git+https://github.com/bmsuisse/playwright-python-bun@v1.64.1-bun.1"`.
The wheel is also attached to every [release](../../releases). Building from git downloads
the driver from the npm registry, so it needs network access but neither Node.js nor npm.

Then install the browser. For headless-only CI the headless shell is enough, and much
smaller than full Chromium:

```sh
playwright install --with-deps --only-shell chromium
```

Not supported: PyInstaller/Nuitka-frozen apps still need bun on the target machine, the
driver is no longer inside the executable.

## bun versions

Only the latest bun is supported; CI builds and tests with it. The wheel does not pin bun
(it runs whatever `bun` is on the machine), so older bun versions are not expected to
work: 1.3.6 and 1.3.9 fail, for example, because they lack the `pfx` TLS option that client
certificates use and differ in Node's HTTP request behaviour that `APIRequestContext`
relies on, and the driver then dies mid-session. 1.4.0 is the first version that passed
our checks. Keep agents on a current bun, including any "install bun if missing" fallback
that pins a version.

`bun-canary.yml` runs weekly: it takes the latest release tag, runs its headless test
suite against the newest bun, and opens an issue if that fails, so a bun release that
breaks an already published wheel is noticed before agents pick it up. To hold an agent on
a known-good bun meanwhile, set `PLAYWRIGHT_BUN_PATH=/path/to/bun`.

## How the fork is kept up to date

`main` is upstream plus a small patch. `.github/workflows/bun-sync.yml` runs daily:

1. `scripts/sync_upstream.py` merges the newest stable upstream tag (`vX.Y.Z`) into `main`,
   deletes upstream's workflows again, sets `UPSTREAM_TAG` and resets `FORK_REVISION` to 1.
2. It pushes `main` and starts `bun-release.yml`, which builds the wheel, runs the tests
   with bun and publishes the release `vX.Y.Z-bun.1` with the wheel attached.

If the merge conflicts, or the tests fail on the new version, the run fails and opens an
issue. Nothing is released until it is fixed.

### When the sync fails

```sh
git fetch upstream --tags            # upstream = microsoft/playwright-python
git merge vX.Y.Z                     # the tag named in the issue
```

Conflicts are only reported for files the fork changed (listed below); upstream's side is
right for everything else. Keep the fork's behaviour in those files, carry over whatever
upstream changed, then `git rm` upstream's workflows (anything in `.github/workflows` that
is not `bun-*.yml`), write `vX.Y.Z` to `UPSTREAM_TAG`, `1` to `FORK_REVISION`, commit,
push, and run the *Release* workflow. Changed the fork's own code instead? Bump
`FORK_REVISION` and run *Release*; the tag becomes `vX.Y.Z-bun.<revision>`.

Scheduled workflows are paused by GitHub after 60 days without repository activity, so
re-enable *Sync upstream* if the Actions tab says so.

## What the fork changes

| File | Change |
| --- | --- |
| `playwright/_impl/_driver.py` | find bun instead of the bundled `driver/node` |
| `setup.py`, `scripts/fetch_driver.py` | build one pure wheel; download `playwright-core` from npm (integrity-checked) instead of `build_driver.py` |
| `UPSTREAM_TAG`, `FORK_REVISION`, `scripts/fork_version.py` | version is `<upstream>+bun.<revision>` |
| `scripts/sync_upstream.py`, `scripts/report_failure.sh` | the upstream merge and failure issue |
| `.github/workflows/bun-*.yml` | CI, release and sync; upstream's workflows are deleted |
| `tests/test_bun_driver.py` | runtime lookup tests |
| `tests/conftest.py`, `tests/{async,sync}/conftest.py`, `tests/test_installation.py` | locate the driver through `compute_driver_executable()`; single wheel |
| `README.md`, `CLAUDE.md`, `FORK.md` | fork notices |

Unused upstream leftovers, deliberately not deleted so merges stay clean:
`scripts/build_driver.py`, `scripts/update_node_version.py`, `NODE_VERSION`.

## Behaviour differences

bun is not Node.js. Upstream's headless chromium suite (everything except the headed
`test_headful` and `page.pause` tests) was run on Node.js 24 and on bun, with
`tests/common`, `tests/sync` and `tests/async` as separate pytest sessions like upstream's
CI:

| runtime | sync | async |
| --- | --- | --- |
| Node.js 24 | 779 passed | 1634 passed |
| bun 1.4.2 | 779 passed | 1634 passed, 1 teardown error (see below) |
| bun 1.4.4 (latest when written) | 778 passed, 1 failed (see below) | 1633 passed, 1 failed (see below) |

- The error message for an untrusted client certificate is worded differently on every
  runtime: `alert unknown ca` on Node.js, `socket hang up (ECONNRESET)` on bun 1.4.2 and
  `TLSV1_ALERT_UNKNOWN_CA` on bun 1.4.4. The request fails either way. The failed 1.4.4
  runs were that test matching the 1.4.2 wording; it now accepts all three.
- `test_screencast.py::test_should_report_callback_errors_and_continue_delivering_frames`
  failed once with a teardown error in one full bun 1.4.2 run (a frame callback that
  raises on purpose while the context closes). It passed in 8 of 8 repeats of the file and
  did not occur on Node.js; treat it as a flaky test unless it starts to recur in CI.
