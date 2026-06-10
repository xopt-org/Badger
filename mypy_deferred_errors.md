# Mypy Deferred Errors

This document captures the full state of `mypy --strict --ignore-missing-imports` on the badger repository as of 2026-06-09. The first run produced **1506 errors in 116 files**. After this PR's mechanical fixes (annotation-only changes, no runtime behavior changes) the count is **1473 errors in 98 files**.

The remaining errors fall into two groups:

1. **Mechanical work not yet done** — straightforward signature additions across GUI components and tests. Listed in §1 with file-by-file scopes for follow-up PRs.
2. **Real issues requiring business-logic review** — not mechanical fixes. Listed in §2 with concrete file:line references and what each one means.

---

## §1. Remaining mechanical work (deferred to follow-up PRs)

These are pure annotation additions. No runtime behavior changes required. Work can proceed file-by-file in independent PRs.

### 1a. Test files — add `-> None` to test functions, type fixture parameters as `Any`

| File | Approx. errors |
| --- | --- |
| `src/badger/tests/test_environment.py` | 40 |
| `src/badger/tests/test_formulas.py` | 39 |
| `src/badger/tests/test_routine_page.py` | 31 |
| `src/badger/tests/test_run_monitor.py` | 27 |
| `src/badger/tests/utils.py` | 17 |
| `src/badger/tests/test_settings.py` | 17 |
| `src/badger/tests/test_routine_runner.py` | 12 |
| `src/badger/tests/test_gui_basic.py` | 11 |
| `src/badger/tests/conftest.py` | 11 |
| `src/badger/tests/test_env.py` | 9 |
| `src/badger/tests/test_routine.py` | 4 |
| `src/badger/tests/test_intf.py` | 7 |
| `src/badger/tests/test_core_subprocess.py` | 8 |
| `src/badger/tests/test_cli_basic.py` | 7 |
| `src/badger/tests/test_core.py` | 6 |
| `src/badger/tests/test_lib_basic.py` | 2 |
| `src/badger/tests/test_factory.py` | 1 |
| `src/badger/tests/test_home_page.py` | 2 |
| `src/badger/tests/test_create_process.py` | 2 |
| `src/badger/tests/test_routine_id.py` (`x-test_routine_id.py`) | 4 |
| `src/badger/tests/x-test_db.py` | 2 |
| `src/badger/tests/test_settings.py` (continued) | — |
| `src/badger/tests/test_measurement_retry_dialog.py` | 2 |
| `src/badger/tests/test_process_manager.py` | 3 |
| `src/badger/tests/multiprocess_logging.py` | 3 |
| `src/badger/tests/mock/plugins/...` | ~10 |

**Pattern**:
- `def test_xxx(...)` → `def test_xxx(...) -> None`
- `def fixture_xxx(mocker, qtbot, request)` → `def fixture_xxx(mocker: Any, qtbot: Any, request: Any) -> ...`
- `points_eval_list = []` → `points_eval_list: list[Any] = []`
- `out, err = "", ""` after `out: str` annotation in `test_cli_basic.py:8-9`.

### 1b. GUI windows / dialogs — add signatures to `__init__`, `init_ui`, `config_logic`, slot handlers

| File | Approx. errors |
| --- | --- |
| `src/badger/gui/windows/load_data_from_run_dialog.py` | 17 |
| `src/badger/gui/windows/settings_dialog.py` | 18 |
| `src/badger/gui/windows/ind_lim_vrange_dialog.py` | 14 |
| `src/badger/gui/windows/lim_vrange_dialog.py` | 11 |
| `src/badger/gui/windows/add_random_dialog.py` | 11 |
| `src/badger/gui/windows/main_window.py` | 12 |
| `src/badger/gui/windows/docs_window.py` | 11 |
| `src/badger/gui/windows/expandable_message_box.py` | 7 |
| `src/badger/gui/windows/edit_script_dialog.py` | 9 |
| `src/badger/gui/windows/var_dialog.py` | 7 |
| `src/badger/gui/windows/terminition_condition_dialog.py` | 11 |
| `src/badger/gui/windows/measurement_retry_dialog.py` | 1 |
| `src/badger/gui/windows/message_dialog.py` | 4 |
| `src/badger/gui/windows/review_dialog.py` | 4 |

**Pattern**:
- `def __init__(self, ...):` → `def __init__(self, ...) -> None:`
- `def init_ui(self):` → `def init_ui(self) -> None:`
- `def config_logic(self):` → `def config_logic(self) -> None:`
- All event-handler slots → `-> None`.

### 1c. GUI components/pages — same mechanical patterns

| File | Approx. errors |
| --- | --- |
| `src/badger/gui/pages/home_page.py` | 40 (mostly logic — see §2) |
| `src/badger/gui/components/run_monitor.py` | 121 (mostly logic — see §2) |
| `src/badger/gui/components/routine_page.py` | 119 (logic-heavy — see §2) |
| `src/badger/gui/components/pydantic_editor.py` | 88 (some logic — see §2) |
| `src/badger/gui/components/var_table.py` | 60 (logic-heavy — see §2) |
| `src/badger/gui/components/data_table.py` | 26 (mostly mechanical) |
| `src/badger/gui/components/navigators.py` | 35 |
| `src/badger/gui/components/archive_search.py` | 26 |
| `src/badger/gui/components/action_bar.py` | 24 |
| `src/badger/gui/components/env_cbox.py` | 22 |
| `src/badger/gui/components/routine_runner.py` | 20 (mostly logic — see §2) |
| `src/badger/gui/components/editable_table.py` | 19 |
| `src/badger/gui/components/collapsible_box.py` | 17 |
| `src/badger/gui/components/bo_visualizer/bo_widget.py` | 17 |
| `src/badger/gui/components/plot_event_handlers.py` | 16 |
| `src/badger/gui/components/bo_visualizer/ui_components.py` | 16 |
| `src/badger/gui/components/syntax.py` | 15 |
| `src/badger/gui/components/routine_item.py` | 15 |
| `src/badger/gui/components/data_panel.py` | 14 (some logic — see §2) |
| `src/badger/gui/components/routine_editor.py` | 12 |
| `src/badger/gui/components/eliding_label.py` | 12 |
| `src/badger/gui/components/pf_viewer/pf_widget.py` | 40 |
| `src/badger/gui/components/process_manager.py` | 4 |
| `src/badger/gui/components/extension_utilities.py` | 2 |
| `src/badger/gui/components/extensions_palette.py` | 11 |
| `src/badger/gui/components/create_process.py` | 4 |
| `src/badger/gui/components/state_item.py` | 3 |
| `src/badger/gui/components/status_bar.py` | 6 |
| `src/badger/gui/components/search_bar.py` | 1 |
| `src/badger/gui/components/labeled_lineedit.py` | 1 |
| `src/badger/gui/components/robust_spinbox.py` | 1 |
| `src/badger/gui/components/reorderable_table.py` | 4 |
| `src/badger/gui/components/obs_table.py` | 1 |
| `src/badger/gui/components/obj_table.py` | 1 |
| `src/badger/gui/components/con_table.py` | — |
| `src/badger/gui/components/filter_cbox.py` | 3 |
| `src/badger/gui/components/generator_cbox.py` | 5 |
| `src/badger/gui/components/constraint_item.py` | 3 |
| `src/badger/gui/components/bo_visualizer/plotting_area.py` | 4 |
| `src/badger/gui/components/analysis_widget.py` | 1 |
| `src/badger/gui/components/analysis_extensions.py` | 1 |
| `src/badger/gui/utils.py` | 9 |
| `src/badger/gui/__init__.py` | 4 (one is logic — see §2) |

### 1d. Plugin scaffolding

| File | Errors |
| --- | --- |
| `src/badger/built_in_plugins/interfaces/default/__init__.py` | 5 |
| `src/badger/built_in_plugins/environments/sphere_2d/__init__.py` | 4 |
| `src/badger/tests/mock/plugins/interfaces/test/__init__.py` | 5 |
| `src/badger/tests/mock/plugins/environments/test/__init__.py` | 3 |
| `src/badger/tests/mock/plugins/environments/multiobjective_test/__init__.py` | 2 |

### 1e. Other core/library modules with remaining mechanical work

| File | Errors |
| --- | --- |
| `src/badger/db.py` | 27 (some logic — see §2.G) |
| `src/badger/log.py` | 23 |
| `src/badger/settings.py` | 18 (mostly logic — see §2.J) |
| `src/badger/routine.py` | 17 (some logic — see §2.E) |
| `src/badger/environment.py` | 29 (some logic — see §2.F) |
| `src/badger/core_subprocess.py` | 29 (mostly logic — see §2.H) |
| `src/badger/archive.py` | 9 |
| `src/badger/logger/__init__.py` | 29 |
| `src/badger/logbook.py` | 4 (one logic — see §2.K) |

---

## §2. Errors requiring business-logic review (NOT addressed in this PR)

These are real type-correctness issues — fixing them changes runtime behavior or requires a design decision. Each entry: file, line(s), what mypy says, why it's deferred.

### A. Truthy-function checks in `core.py`

`src/badger/core.py:108,132,136,165,169` — code like:
```python
if states_callback and (states is not None):
if evaluate_callback:
if dump_file_callback:
```
Mypy: `[truthy-function]`. A function object is always truthy — these checks always pass. The intent appears to be `is not None`, but the parameters are typed `Callable[..., Any]` (non-Optional) except `dump_file_callback`. **Decision needed**: does each call site pass `None` for these callbacks, or always a callable? If never `None`, drop the checks; if sometimes `None`, change type to `Optional` and check `is not None`.

### B. Unguarded `Optional` attribute access — `run_monitor.py`

`src/badger/gui/components/run_monitor.py` — `self.routine` is initialized to `None` and accessed without None checks throughout. Specific lines:
- 109 (`vocs` property)
- 467, 469, 471, 473, 475 (`start()`)
- 503, 528, 538, 547 (data accessors)
- 602, 605, 617 (constraint plotting)
- 654, 655 (run_filename access)
- 688, 693 (routine + environment access)
- 795, 901, 909 (more environment / vocs)
- 956, 968, 969, 970 (vrange_hard_limit)
- 1053, 1107, 1109, 1115–1118, 1149–1152, 1161–1165 (more cascading)

**Decision needed**: either
- Restructure so `self.routine` becomes non-Optional after a setter is called (and all access goes through that setter), or
- Add `if self.routine is None: return` guards at the top of every method that touches it.

Also: `run_monitor.py:281–350` has `Cannot determine type of "plot_con"/"plot_obs"` errors — class attributes referenced before being assigned in `__init__`. Same issue as below in `routine_page.py`. These are forward-reference bugs in the class init path.

### C. Unguarded `Optional` attribute access — `data_panel.py`

`src/badger/gui/components/data_panel.py:139,170,226,267,272,347,382` — similar pattern: `self.run_monitor` or similar set to `None` then accessed. Plus:
- Line 181: `get_data_from_dialog` declared `-> None` but caller uses return value (`func-returns-value`).
- Line 267, 382: missing dict generic args.

### D. Unguarded `Optional` access — `home_page.py`, `var_table.py`

`src/badger/gui/pages/home_page.py:306,546,547,548,596,990` — `Item "None" of "Any | None" has no attribute "data"` etc.
`src/badger/gui/components/var_table.py:540,541,637,645` — `"None" has no attribute "get_variable"/"get_bounds"/"get_info"` and `Item "None" of "Any | None" has no attribute "text"`.

Same pattern: attribute initialized to `None`, accessed unconditionally.

### E. `routine.py:101,102` — wrong type annotation on `data` field

```python
@validate_data
def evaluate_data(self, data: dict) -> dict:
    ...
    new_index = max(self.data.index, default=-1) + 1
    ...
    self.data.sort_index(...)
```
But `self.data` is annotated as `dict[Any, Any]`. The code expects a pandas DataFrame. **Decision needed**: the field type is wrong; should be `DataFrame | None`. Fixing reveals downstream callers expect dict-style access.

### F. `environment.py` — multiple typing issues

- **Line 223**: `def add_observation(self, callable=None) -> bool:` — uses bare `callable` (the builtin) as a type. Replace with `Callable[..., Any] | None`.
- **Line 285**: `__call__` declared `-> float` but actually returns `float | list[float]`. Need to widen return type or split into two methods.
- **Lines 298–324**: `Returning Any from function declared to return "dict"` — internal return-type drift. Several functions have explicit `-> dict[Any, Any]` but actually return `Any`.
- Lines 18, 36, 42, 82–83, 154, 188, 258, 304, 316, 327, 331 — missing annotations (mechanical).

### G. `db.py:109,128,148,149,174,339` — untyped `@db.commit`-style decorators

`Untyped decorator makes function "save_routine" untyped`. The SQLAlchemy / decorator library lacks type stubs. **Decision needed**: either accept `# type: ignore[misc]` per decorated function, or wait for upstream stubs.

Plus `db.py:33,38,56,61,79,92,210,303,358,375,388,400,432` — straightforward missing annotations (mechanical).

### H. `core_subprocess.py` — multiprocessing primitives used as types

```python
event: multiprocessing.Event   # Event is a factory, not a type
queue: multiprocessing.Queue   # missing generic param
pipe: multiprocessing.Pipe     # Pipe returns tuple, not a type
```
Lines 37–39, 132–139, 179, 281, 285, 287, 289, 291, 329–349, 359–375.

**Fix**: import the actual types from `multiprocessing.synchronize` (`Event`), `multiprocessing.connection` (`Connection`), `queue.Queue`. Non-trivial — affects many call sites and signatures across `log.py`, `routine_runner.py`, `create_process.py`.

### I. `routine_page.py` — multiple structural issues

`src/badger/gui/components/routine_page.py`:
- Lines 102, 104, 106: function declared `-> str` but returns tuples. Pick one.
- Lines 477, 824: `Incompatible types in assignment (expression has type "list[dict]", variable has type "dict")` — variable reused with mismatched types.
- Lines 512, 545, 584, 861, 897, 940, 1050, 1098, 1378: `Cannot determine type of "configs" / "archive_search"` — class attributes referenced before assignment in init flow. Init method order is fragile.
- Lines 551, 903: `Unpacking a string is disallowed` — code does `a, b, c = some_string` where the runtime value happens to be a tuple sometimes. Genuine bug or unclear intent.
- Lines 1176, 1280–1282: `List item N has incompatible type "float"/"bool"; expected "str"` — heterogeneous list passed where homogeneous expected.
- Lines 1245, 1273, 1308, 1394: `Item "None" of "Any | None"` not iterable / indexable.
- Lines 1903, 1907, 1911: more None-attribute access.

### J. `settings.py` — `ConfigSingleton` pattern not modeled

Lines 137, 140, 142, 194, 202, 212, 219, 247, 391, 406, 481, 492, 541, 1683, 1684, 1685, 1686, 1687, 1688, 1689, 1690, 1691, 1694:
- `"ConfigSingleton" has no attribute "user_flag"` etc. — singleton attributes set dynamically.
- `Cannot determine type of "_config"`.
- `Argument 1 to "copytree" has incompatible type "Traversable"; expected "str | PathLike[str]"`.

**Decision needed**: refactor `ConfigSingleton` with explicit `__slots__` / class-level annotations, or sprinkle `cast()`/`# type: ignore`.

### K. `logbook.py:60` — `Element` type-var bound

`Value of type variable "_Tag" of "Element" cannot be "None"` — passing `None` where `xml.etree.ElementTree` expects a string tag. Likely a real bug if `name` is ever None at runtime.

### L. `gui/__init__.py:85` — `sys.excepthook` signature

```python
sys.excepthook = my_hook
```
where `my_hook`'s third parameter is `TracebackType` (non-Optional) but `sys.excepthook` expects `Optional[TracebackType]`. Need to add a None guard inside the hook.

### M. `pydantic_editor.py` — list/tuple variance and BaseModel typing

Lines 150, 154, 171, 189, 254 in `src/badger/gui/components/pydantic_editor.py`:
- `Incompatible types in assignment (expression has type "list[Any]", variable has type "tuple[Any, ...]")` — type narrowing breaks because variable is reused.
- `Argument "main" to "BadgerResolvedType" has incompatible type "Any | type[Any] | <typing special form> | None"; expected "type[Any] | None"` — pydantic generic resolution returns more types than annotated.
- `Incompatible types in assignment (expression has type "BadgerResolvedType | None", variable has type "BadgerResolvedType")`.

These need careful review of the pydantic-resolution machinery.

### N. `pydantic_editor.py:1110` — redundant cast

Already addressed in code; the `cast` was redundant but mypy says so as `[redundant-cast]`. Just delete the call.

### O. Untyped pydantic decorators in `routine.py`

Lines 52, 143: `@validate_model`, `@validate_data` make decorated methods untyped. Cascade is the same as §G. Wait for upstream pydantic typing fix or add `# type: ignore[misc]`.

### P. Stale `# type: ignore` comments (mechanical)

Files with `[unused-ignore]` errors — just delete the comments:
- `src/badger/gui/components/pydantic_editor.py`: lines 668, 674, 931
- `src/badger/gui/components/plot_event_handlers.py`: lines 57, 76, 81, 318, 319
- `src/badger/gui/components/pf_viewer/pf_widget.py`: lines 76, 77
- `src/badger/gui/components/bo_visualizer/bo_widget.py`: lines 51, 52, 120, 129, 241
- `src/badger/gui/windows/settings_dialog.py`: line 181

### Q. `editable_table.py:263` — unbound `ParamSpec`

`ParamSpec "P" is unbound`. The class uses `ParamSpec` outside a generic context. Needs refactor to either remove the `ParamSpec` or make the surrounding class generic.

### R. `var_table.py:263,333` — duplicate attribute assignment (`[no-redef]`)

Class attributes `selected` and `addtl_vars` assigned in two places. Needs single-source declaration in `__init__`.

### S. Test file logic mismatches

- `src/badger/tests/test_environment.py:126` — dict literal type mismatch (`Dict entry 0 has incompatible type "str": "list[int]"; expected "str": "float"`). The test is feeding wrong-shape data.
- `src/badger/tests/test_core.py:64` — `Incompatible types in assignment (expression has type "dict[Any, Any]", variable has type "None")` — variable initialized as None then assigned dict; should be `dict | None`.
- `src/badger/tests/x-test_db.py` — file prefixed `x-`, not collected by pytest. Likely dead code; could be deleted.
- `src/badger/tests/utils.py:25,53,94,124,162,164` — `Argument after ** must be a mapping, not "Collection[str]"` — repeatedly unpacks a Collection as kwargs. Actual bug if executed; the file may be unused or only partially exercised.

---

## §3. Suggested follow-up plan

1. **Mechanical PR for tests** (§1a) — adds ~200 `-> None` annotations. Low risk, high signal; gates future strictness on test code.
2. **Mechanical PR for GUI windows/dialogs** (§1b) — ~120 annotations.
3. **Mechanical PR for GUI components leaf files** (the smaller files in §1c).
4. **Logic PR: callbacks & Optional core types** (§A, §B, §C, §D) — change `self.routine` etc. to proper `Optional` and add guards.
5. **Logic PR: multiprocessing types** (§H) — `multiprocessing.synchronize.Event` etc. across `core_subprocess.py`, `log.py`, `routine_runner.py`.
6. **Logic PR: settings.py + ConfigSingleton** (§J) — restructure or cast.
7. **Logic PR: routine_page.py, run_monitor.py, var_table.py large files** (§B, §I, §R) — biggest, most fragile; do last.

Each can be a separate PR; none of them block each other except where noted.

---

## §4. Counts at end of this PR

- **Errors before this PR**: 1506
- **Errors after this PR**: 1473 (down 33)
- **Errors after PyQt5-stubs install**: jumped to 1621 first (Qt now visible to mypy), then dropped to 1473 after fixing core/library + stubs benefit. Net effect positive vs. baseline despite the stub-revealed new errors.
- **Files fully clean now**: `stats.py`, `errors.py`, `extension.py`, `formula.py`, `interface.py`, `logger/util.py`, `logger/observer.py`, `actions/__init__.py`, `actions/doctor.py`, `actions/run.py`, `actions/routine.py`, `actions/intf.py`, `actions/generator.py`, `actions/env.py`, `actions/config.py`, `actions/install.py`, `actions/uninstall.py`, `__main__.py`, plus partial in `core.py`, `factory.py`, `utils.py`.
