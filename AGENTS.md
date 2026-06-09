# AGENTS.md

## Overview

Badger is a PyQt5 GUI/CLI optimization tool for particle accelerators. It wraps the [Xopt](https://github.com/xopt-org/Xopt) library and uses a plugin system for environments and interfaces. The package name on PyPI/conda is `badger-opt`, but the Python import is `badger`.

## Development Setup

```bash
pip install -e ".[dev]"
pre-commit install
```

Python 3.11–3.13 only. PyQt5 is a hard dependency even for non-GUI code paths (`badger.utils` imports `PyQt5.QtWidgets` at the top level).

## Running Tests

```bash
python scripts/run_tests.py
```

Or directly with pytest (tests are at `src/badger/tests/`):

```bash
pytest src/badger/tests/ -v -vrxs
```

All 144 tests should pass. GUI tests use `pytest-qt` and require a display server (the CI uses Xvfb on Linux). On macOS, set `QT_MAC_WANTS_LAYER=1` if qtbot interactions fail.

### Test gotchas

- **Tests mutate the real user config file.** The `conftest.py` module-scoped fixture overwrites `BADGER_PLUGIN_ROOT`, `BADGER_ARCHIVE_ROOT`, etc. in the user's actual `config.yaml` (macOS: `~/Library/Application Support/Badger/config.yaml`), then restores values after the test module completes. If tests crash mid-run, your config may be left in a test state — run `badger doctor -r` to reset.

- **`ConfigSingleton` persists across tests.** It is a true singleton (`_instance` class variable). Tests that need a fresh config must set `ConfigSingleton._instance = None` in teardown. The test `conftest.py` relies on the singleton already existing from module-level imports in `factory.py`/`archive.py`.

- **GUI tests force `fork` multiprocessing.** Tests explicitly call `multiprocessing.set_start_method("fork", force=True)`. This produces deprecation warnings on macOS about multi-threaded fork — these are expected and harmless in test context.

- **`suppress_popups` is autouse.** All tests automatically mock `ExpandableMessageBox.exec_` to prevent Qt dialogs from blocking test execution.

- **Disabled tests use `x-` prefix.** Files like `x-test_db.py` are excluded from pytest collection (they don't match the `test_*.py` pattern). These require `BADGER_DB_ROOT` to be configured.

- **Coverage reports show warnings.** The `--cov=badger/` in `pyproject.toml` doesn't align with the `src/` layout. Tests pass but coverage data isn't collected. This is a known issue.

## Linting and Formatting

Pre-commit runs `ruff check --fix` and `ruff format`. The ruff config:
- Extends default rules with `TID252` (relative import checks)
- Ignores `E722` (bare excepts) — these exist in the codebase intentionally for now
- Pre-commit also blocks direct commits to `main` (`no-commit-to-branch` hook)

## Architecture: Critical Patterns

### Module-level side effects on import

These modules execute code at import time that reads config and may create directories:
- `badger.factory` — reads `BADGER_PLUGIN_ROOT`, appends to `sys.path`, scans plugins
- `badger.archive` — reads `BADGER_ARCHIVE_ROOT`, creates directory if missing
- `badger.logbook` — reads `BADGER_LOGBOOK_ROOT`, creates directory if missing
- `badger.db` — reads `BADGER_DB_ROOT` (optional, gracefully skipped if missing)

Importing any of these modules requires a valid config file to exist. If you're writing code that imports from these modules, be aware that the `ConfigSingleton` will be initialized as a side effect.

### ConfigSingleton

`badger.settings.ConfigSingleton` is initialized once per process. Multiple calls to `init_settings()` return the same instance. The subprocess optimization process re-initializes its own singleton by passing the config file path explicitly.

The config file location is OS-dependent:
- macOS: `~/Library/Application Support/Badger/config.yaml`
- Linux: `~/.config/config.yaml`
- Windows: `%APPDATA%/config.yaml`

### Plugin system

Plugins live under `BADGER_PLUGIN_ROOT` (user-configured path) with this structure:
```
BADGER_PLUGIN_ROOT/
├── __init__.py          (auto-created if missing)
├── environments/
│   └── my_env/
│       ├── __init__.py  (must export `Environment` class)
│       └── configs.yaml (required: name, version, dependencies, optionally interface)
└── interfaces/
    └── my_intf/
        ├── __init__.py  (must export `Interface` class)
        └── configs.yaml (required: name, version, dependencies)
```

The plugin root is added to `sys.path` — plugins are imported as `environments.my_env` and `interfaces.my_intf`. Plugins are lazy-loaded: `scan_plugins` only registers names, `load_plugin` does the actual import on first access.

### Environment metaclass (`EnvMeta`)

`BaseEnvironment` uses a custom metaclass that automatically wraps methods at class definition time:
- `get_bounds` → wrapped with `validate_bounds` (checks bound format/ordering)
- `get_observables` → wrapped with `process_formulas` (handles backtick formula syntax)
- `set_variables` → wrapped with `validate_setpoints` (enforces variable bounds)

Do NOT manually apply these decorators in subclasses — the metaclass handles it.

### Routine extends Xopt

`badger.routine.Routine` inherits from `xopt.Xopt` (a Pydantic model). The `@model_validator(mode="before")` does heavy lifting:
- Resolves generator by name string → class instance
- Instantiates environment from dict (via the factory/plugin system)
- Creates an `Evaluator` closure that captures the environment instance
- Handles DataFrame conversion for `data` field

When constructing a `Routine` programmatically, the `environment` field can be either an instantiated `Environment` object or a dict with a `"name"` key (which triggers plugin lookup).

### Optimization runs in a subprocess

The GUI spawns optimization as a `multiprocessing.Process` (see `core_subprocess.py`). Communication:
- `mp.Queue` — passes routine filename and receives error tuples
- `mp.Pipe` — streams `(data, generator)` tuples back to GUI
- `mp.Event` — `stop_event`, `pause_event`, `wait_event` for flow control

The subprocess reinitializes `ConfigSingleton`, reimports `archive`, and configures its own logging via the centralized `QueueHandler`/`QueueListener` system.

### `BadgerError` triggers a GUI popup

Raising `BadgerError` calls `show_message_box()` in its `__init__`, which opens a Qt dialog. This means raising this error in non-GUI contexts (tests, CLI, subprocess) will crash unless the message box is mocked. Tests handle this via the `suppress_popups` autouse fixture.

### Formula/expression syntax

Observable names containing backticks are treated as mathematical expressions. Variable references use `` `var_name` `` syntax within the expression. The formula engine uses numpy functions in a restricted namespace. Example: `` `x0`**2 + `x1`**2 ``.

## Archive file conventions

Run data is stored as YAML files in a date-based hierarchy:
```
BADGER_ARCHIVE_ROOT/
└── 2024/
    └── 2024-09/
        └── 2024-09-10/
            └── env_name-2024-09-10-155408.yaml
```

Filenames follow `{env_name}-{YYYY-MM-DD-HHMMSS}.yaml`. The `load_run` function parses the filename to reconstruct the path — so renaming archive files will break loading.

Temporary runs (pre-archive) go to `BADGER_ARCHIVE_ROOT/.tmp/` with `.tmp-BadgerOpt-{timestamp}.yaml` naming.

## Version management

`setuptools_scm` generates `src/badger/_version.py` from git tags. Never edit this file manually. The version format is `{tag}.dev{N}+g{short_hash}` for non-tagged commits.

## GUI structure

The GUI is a single-window PyQt5 app (`BadgerMainWindow`) with:
- One page: `home_page.py` (contains routine editor + run monitor)
- Components in `gui/components/` — the naming doesn't always match the visual element (see `GUI_GUIDE.md` for the mapping)
- Dialogs in `gui/windows/`

The `run_monitor.py` component handles live plotting via pyqtgraph. The `routine_runner.py` manages subprocess lifecycle. The `process_manager.py` maintains a queue of pre-spawned processes for faster run starts.

## Module docstrings

Every non-empty Python file under `src/badger/` (excluding `src/badger/tests/`) must have a module-level docstring. The docstring should:
- Describe what the module contains and its role in the Badger system
- Be 2–4 lines, focused and informative (no filler like "This module provides...")
- Be updated when the module's primary responsibility changes (e.g., classes are moved in/out, the module is split)

A pre-commit hook (`check-module-docstrings`) enforces presence. Empty `__init__.py` files are exempt.

## Common pitfalls

1. **Don't import `badger.factory` in isolation tests** without ensuring config is set up — it will raise `BadgerConfigError` at import time.

2. **The test `mock/plugins/environments/test/` environment uses `torch`** — it computes observables via `torch.tensor`. This is an actual test dependency not listed in `[dev]` extras (it comes transitively via `xopt`).

3. **`Interface.reset_interface()`** is called after process fork — use it to reset any non-fork-safe state (file descriptors, connections, etc.) in custom interfaces.

4. **The `db.py` module is semi-deprecated** — it requires `BADGER_DB_ROOT` config which is not in the default `BadgerConfig` model. The `x-test_db.py` and `x-test_routine_id.py` files test this functionality but are excluded from normal test runs.

5. **`utils.py` has Qt dependencies** — `BlockSignalsContext` and related utilities import from `PyQt5.QtWidgets` at the module level, so `badger.utils` cannot be imported without PyQt5 installed.
