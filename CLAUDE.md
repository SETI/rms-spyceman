# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo state

Active work in progress. `import spyceman` now succeeds, as do the host and solar-system
catalogs; `Recipe.furnish()` loads kernels into SPICE end to end.
`src/spyceman/hosts/Galileo/` is an empty placeholder.

See `critiques/` for the current review. Every finding there is closed and carries a dated
status note, and the "What to do next" section at the end is now worked through as well.

Two optimizations make catalog imports tolerable — Cassini went from 141 s to 1.3 s.
Both are transparent, and both were verified by importing the catalogs with the
optimization disabled and diffing every kernel's resolved metadata.

- `_CSPYCE.get_body_aliases()` and `get_frame_aliases()` are memoized in
  `src/spyceman/_cspyce.py`. Every function that can change SPICE's body or frame tables is
  wrapped there to clear the cache. **If you add a call that alters those tables without
  going through `_CSPYCE`, call `clear_alias_caches()`**, or NAIF ID resolution goes
  stale.
- `_utils._fast_day_sec_from_iso()` recognizes `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS.fff`
  directly instead of invoking `julian`'s pyparsing grammar; any other shape returns
  `None` and falls back. It **trusts the field values** rather than checking them, because
  catalog dates are machine generated — so `validate_release_date('2019-02-29')` returns
  `'2019-03-01'` instead of raising. Before widening the pattern, remember that nothing
  downstream validates: `julian.day_from_ymd()` rolls `2020-02-30` into March, and that is
  why the hyphens are required (`'12345678'` would otherwise parse as a date).

## Layout and tooling

The package lives at `src/spyceman/`. Tests are in `tests/`, docs in `docs/`.

- Bootstrap: `./scripts/setup-venv.sh` (creates `venv/`, installs `-e ".[dev]"`)
- All checks: `./scripts/run-all-checks.sh` (parallel by default; `-s` sequential,
  `-c` code only, `-d` docs only, `--pytest` / `--sphinx` / … for one check)
- Single test: `python -m pytest tests/test_utils.py -k <name>`
- Docs: `./scripts/read-docs.sh` builds and opens the HTML

Tests marked `slow` import a full kernel catalog and are **deselected by default** through
`addopts = [..., "-m", "not slow"]`. Run them with `pytest -m slow`; they take about four
seconds, against under three for everything else. The marker dates from when they took two
and a half minutes; it is worth keeping only while catalog imports remain the slowest thing
the suite does.

`tests/test_docstrings.py` enforces the docstring standard in `.claude/rules/docstrings.md`
over every function in the package, including the 90-column limit. A new function without a
conforming docstring fails the suite.

`tests/test_selection.py` and `tests/test_furnish.py` cover which kernels get chosen and
what gets loaded. They rely on fixtures in `tests/conftest.py`: `unique_name` because
`_KernelInfo` keeps a process-wide registry that refuses to redefine a basename, and
`spice_sandbox` because the furnish record and the debug/download switches are module-level
state. **Assert on the exact basenames chosen or furnished**, never merely that a call
returned — §6.20 was a kernel silently omitted while every call reported success.

`mypy` and `stubtest` are switched off in `scripts/run-all-checks.sh` — the source
carries no type annotations and there are no `.pyi` stubs.

## Ruff runs "F" only; the formatter never runs

`ruff check` is enabled in all three places it runs: `select = ["F"]` in
`[tool.ruff.lint]`, `ENABLE_RUFF_CHECK` in `scripts/run-all-checks.sh`, and the Ruff step
in `.github/workflows/run-tests.yml`. Changing the rule set means changing all three
together. Both the script and CI lint `src tests programs`, and so does the flake8
continuation-line step beside them.

The `exclude` glob in `[tool.ruff]` skips the machine-generated tables. Check what it
actually covers with `ruff check --show-files src/spyceman` before changing it: `*` there
is a glob wildcard, not a repeat of the character class before it, so the earlier
`_[A-Z0-9_]*.py` also matched every `__init__.py` and left all five unlinted -- which is
how four undefined names sat in `hosts/Cassini/__init__.py` without CI noticing.

**`ruff format` is deliberately off and should stay off.** The house style is
column-aligned (see Code style below) and the formatter would reflow every aligned block.
`ENABLE_RUFF_FORMAT` defaults to false and there is no CI step for it.

`ignore = ["E741", "I001"]` is a **permanent decision, not deferred work.** Unlike the
deleted `per-file-ignores`, these are not to be re-derived from a clean run: both describe
the house style, so they stay off whatever `select` grows to include. E741 (a variable
named `l`) is already ignored in `.flake8`, so this keeps the two linters consistent;
I001 would reorder the column-aligned import blocks. Note that a rule named explicitly in
`--select` on the command line overrides `ignore`, which is Ruff's precedence, not a bug —
widen `select` in `pyproject.toml` if you want the ignore list respected.

F is Pyflakes: undefined names and unused imports, nothing else. That is the failure mode
this codebase actually suffers from, and enabling it immediately found a live one. Adding
a category is a real project, not a config edit — the wider set
(`E,W,I,UP,B,SIM,C4,A,N,PT,RUF`) still reports 137 findings beyond the two ignored above,
most of which describe the house style rather than defects:

- **E402** (21) — imports mid-file are intentional here; `.flake8` disables it too.
- **N999/N801/N802/N805** (22) — the capitalized host and body modules (`Cassini`,
  `Mars.py`) and the lowercase descriptor classes (`_local_dict`, `_tkdict_desc`) are
  deliberate.
- **RUF005** (14), **SIM108** (10) — style preferences.
- **RUF012** (7) — the mutable class-level registries in `_KernelInfo` are the design.
- **PT006/PT011** (13) — pytest idiom in the test suite.

Worth a look if someone takes it further: **B904** (2, `raise ... from` inside `except`,
which loses the original traceback), **B006** (7, mutable argument defaults), **B905** (9,
`zip` without `strict`).

The old `per-file-ignores` were deleted rather than left in place, because a stale
suppression silently exempts a file long after the bug it described is gone. Re-derive any
new ones from a clean run. `flake8 --select=E12,E13` still runs and still gates
continuation-line indentation, which Ruff implements no rule for.

The same "do not leave a stale suppression" note applies to the
`md009`/`md012`/`md022`/`md032` PyMarkdown rules, which exist only because `README.md`
and `CONTRIBUTING.md` have not been reformatted.

`fail_under` in `[tool.coverage.report]` and the project target in `codecov.yml` are 30,
against an actual 35.5%. It is a floor that catches a collapse, not a target; raise it
toward rms-polymath's 90 as more behavioral tests land. The codecov *patch* target is
still 0, because much of the package has no behavioral tests for new code to model.

## Environment variables

The **code** is authoritative; the README's `SPICE_PATH` / `SPICE_DOWNLOADS` are stale.

- `SPICEPATH` — colon-separated local kernel directories (required)
- `SPICE-DOWNLOADS` — destination for downloaded kernels

## Code style

`.flake8` disables ~35 whitespace and formatting checks **on purpose**. Column alignment
is the house style, not an accident — never reflow aligned code to PEP8 defaults.

- Wrap at **90 columns**. E501 is off, but 90 is the de-facto limit and the banner width.
- Align imports and assignments in columns:
  ```python
  from spyceman._cspyce     import _CSPYCE
  from spyceman._kernelinfo import _KernelInfo
  NAME    = 'MARS'
  BODY_ID = 499
  ```
- Single quotes; f-strings for interpolation. No type annotations anywhere — don't add them.
- Imports may appear mid-file, right before first use (E402 is off). This is intentional.
- Every hand-written module opens and closes with a 90-character `#` banner, and separates
  sections with the same banner plus a title line:
  ```python
  ##########################################################################################
  # spyceman/<path>.py: one-line purpose
  ##########################################################################################
  ```
- Host and planet modules keep the public namespace clean by giving module-level
  temporaries a leading underscore (`_rule`, `_lsk_source`). Some older modules instead
  `del` them at the end of the file; both idioms are in use.
- Docstrings follow `.claude/rules/docstrings.md`: Google style with a `Parameters:`
  header — never `Args:` or `Inputs:` — a `Returns:` section only where the function
  returns a value, and 90-column wrapping.

## Architecture

- `_CSPYCE` (`src/spyceman/_cspyce.py`) **is** the `cspyce` module, monkey-patched in
  place with the flag-returning variants of `bodn2c` and friends and with memoized alias
  lookups. It is private: nothing re-exports it from `spyceman/__init__.py`. There is no
  `spicepy` fallback and no `SPICEMODULE` switch: the package uses cspyce-only APIs
  (`spkcov(...).as_intervals()`, `ckcov(needav=...)`, `.flag`), so the alternative never
  ran. Reach SPICE through `_CSPYCE` rather than importing `cspyce`, so that every
  mutator stays wrapped.
- `Kernel` is the abstract base. Subclasses: `KernelFile` (one file), `KernelSet` (mutually
  compatible files), `KernelStack` (prioritized load order), `Metakernel` (mixed ktypes).
  `Recipe` is the user-facing switchable collection.
- `_KTYPES` in `src/spyceman/_ktypes.py` is ordered by load dependency
  (`META, LSK, STAR, PCK, DSK, FK, IK, SCLK, CK, SPK`). **Do not reorder it.**
- `Rule` (`src/spyceman/rule.py`) is a pattern mini-DSL, not plain regex: date tags like
  `(YYYYMMDD)`, version tags like `(N+)`, plus named captures. Rules self-register keyed by
  extension and field count; more embedded fields wins.
- `_spicefunc()` (`src/spyceman/_spicefunc.py`) is the factory that builds every public
  `spk()`, `pck()`, `ck()`. Their shared docstring comes from `DOCSTRING_TEMPLATE`. To add
  a body or mission, follow `src/spyceman/solarsystem/Mars.py`: IDs → `Rule` →
  `_spicefunc(known=..., unknown=...)`. It is internal and is not re-exported from
  `spyceman/__init__.py`.
- `_UPPERCASE.py` files (`_MARS_SPKS.py`, `_RECONSTRUCTED_CKS.py`, …) are **machine-generated**
  `KTuple` tables. Regenerate with `python programs/ktupler.py`; do not hand-edit. They
  use an 80-column banner rather than 90, and ruff is configured to skip them. The
  generator itself is not skipped: `programs/` is linted alongside `src` and `tests`, is
  held to the docstring standard, and `tests/test_ktupler.py` covers the time formatting
  and the version-numbering that a table depends on. `programs` is on the pytest
  `pythonpath` so the tests can import it.
- Importing a host or planet module executes SPICE calls at import time and may emit
  warnings. `docs/conf.py` mocks `cspyce`, `julian`, `textkernel`, and `portion`
  for this reason.
- `src/spyceman/recipe.py` uses custom `property` subclasses under a `# Hacks to allow some
  convenient syntax` banner, so class-level attribute access is deliberately non-standard.

## Repo etiquette

- Commit directly to `main`; that matches the existing history. CONTRIBUTING.md's
  pull-request flow applies to outside contributors.
- GitHub Issues: label bugs `A-Bug` and enhancements `A-Enhancement`, with no other labels.
  The issue templates in `.github/ISSUE_TEMPLATE/` apply these automatically.
- Never file security issues publicly — email <matt@seti.org>.
