# Code critique: rms-spyceman — 2026-08-16

Scope: the hand-written modules of `src/spyceman/` (~6,400 lines across 20 core modules,
plus the `hosts/` and `solarsystem/` packages) as revised on 2026-08-16. The
machine-generated `_UPPERCASE.py` KTuple tables (~13,600 lines) were audited only for
import-level breakage, not content.

Findings tagged **[confirmed]** were reproduced by executing the code. Because
`import spyceman` still fails, most reproductions were done by executing a module body in
isolation with its imports stubbed, or by lifting a function verbatim into a test script;
where that was done it is stated. Findings without the tag come from reading.

This review is independent of the one it replaces. Every claim carried forward was
re-checked against the current source, and several previous findings are now closed.

## Summary

> **Status as of 2026-08-16:** §1.1 through §1.5 have been fixed, ruff has been disabled
> across all three surfaces where it ran, and `ktupler.py` was found in `programs/` rather
> than deleted. Everything else below is open. Each affected section carries its own note;
> the body text describes the code as it stood at the time of the reading and is kept
> unedited as the record of it.

**This revision was a naming and structure pass, not a bug-fix pass.** That is worth
stating plainly, because the diff is large — 3,400 changed lines across 40 files — and
its size does not reflect a change in the library's behavior.

Measured by comparing abstract syntax trees with docstrings stripped, `kernel.py`,
`kernelstack.py`, and `rule.py` contain **zero** code changes. `recipe.py` contains two
(an `import re` moved). What did change:

- `spicefunc.py` → `_spicefunc.py`, and `spicefunc()` → `_spicefunc()`, with call sites
  updated across eight modules.
- A new `hosts/_utils.py`, holding `_intersect_basenames()` moved out of `_utils.py`.
  This module was previously imported by `hosts/Cassini/spk.py` but did not exist.
- `ktupler.py` deleted.
- `_localfiles.initialize()` replaced by `_get_spicepath()`, with `walk()` now defaulting
  to `SPICEPATH` when called with no arguments.
- A new convention: module-level temporaries are given a leading underscore (`_rule`,
  `_key`, `_body_id`, `_lsk_source`) instead of being `del`-ed at the end of the file.
- String formatting modernized to f-strings throughout.

Three real defects were fixed: `_downloads.py` now parses and imports `datetime`;
`_KernelInfo.match()` now returns the set it computes; and `_intersect_basenames()` now
has `KernelFile` in scope. Those are noted in §2.

Against that, **the refactor introduced seven new defects, four of which are fatal at
import time** (§1). Two of them are the classic signature of an incomplete rename: a
definition was renamed and its references were not. The rest of the library's defects —
the inoperative `Rule` engine, the unhashable `Kernel`, the recursive `KernelFile
.basenames`, the missing `KernelFile.basename` — are present and unchanged.

The net effect is that the package now fails *later* than it did, which is progress of a
sort, but it fails for the same underlying reason: this code still has never been run.
`import spyceman` currently dies at `_kernelinfo.py:547`, and behind that failure sit at
least three more module-level errors that no execution has yet reached.

Priorities, in dependency order: close the four new import-time breakages in §1, which
are all small; then repair `Rule` and `_KernelInfo` together with tests, because they are
the foundation everything else stands on; then `Kernel`/`KernelFile`. Details in
**Recommended priorities** at the end.

---

## 1. Defects introduced by this revision

> **Status: §1.1 through §1.5 were fixed on 2026-08-16.** Each carries its own note
> below. §1.6 and §1.7 remain open. The text describes the code as it stood before the
> fixes and is kept unedited as the record of that reading.

### 1.1 `spyceman/__init__.py` imports a module that no longer exists — **blocking** [confirmed]

> **Fixed 2026-08-16.** The export was dropped rather than repointed: the rename made
> both the module and the function private, nothing outside `hosts/` and `solarsystem/`
> uses it, and re-exporting `_spicefunc` would have collided with the submodule
> attribute of the same name. An explicit `__all__` was added in its place.

`src/spyceman/__init__.py:14`

```python
from spyceman.spicefunc   import spicefunc
```

The module was renamed to `_spicefunc.py` and the function to `_spicefunc()`. Every other
call site was updated — `General.py`, `Saturn.py`, `Jupiter.py`, `Mars.py`, `Neptune.py`,
`Pluto.py`, `Uranus.py`, `Cassini/ck.py`, `Cassini/spk.py`, `Cassini/__init__.py`,
`Voyager/__init__.py` — but the package's own `__init__` was not.

```text
src/spyceman/spicefunc.py exists: False
__init__.py still does:           from spyceman.spicefunc   import spicefunc
```

Line 12 (`from spyceman.recipe import Recipe`) currently raises first, which is the only
reason this has not been seen. Fix line 12's cause and this becomes the next failure.

Note also that the rename makes the factory private. `_spicefunc` is no longer part of the
public API, yet `__init__.py` was evidently intended to export it. Decide which it is: if
it stays private, drop line 14; if it is public, it should not carry the underscore.

### 1.2 `hosts/Cassini/_utils.py`: a rename left ten dangling references — **blocking** [confirmed]

> **Fixed 2026-08-16.** All ten references renamed to `_BODY_ID`; the module body now
> executes cleanly in isolation.

`src/spyceman/hosts/Cassini/_utils.py:8` defines `_BODY_ID = -82`. Lines 41–45 and 50–54
still refer to `BODY_ID`:

```python
  8    _BODY_ID = -82
 ...
 41        'VENUS'   : {BODY_ID, 2, 299},
 42        'EARTH'   : {BODY_ID, 3, 301, 399},
```

Executing the module body in isolation, with `Saturn` stubbed:

```text
NameError: name 'BODY_ID' is not defined
```

Ten occurrences; `ruff --select F821` reports all ten. This module is imported by
`Cassini/ck.py` and `Cassini/spk.py`, so the entire Cassini host package is unreachable.

### 1.3 `_AS_FLOWN_CKS.py` lost its `KTuple` import — **blocking** [confirmed]

> **Fixed 2026-08-16.** `from spyceman.kernelfile import KTuple` restored; all 104
> KTuples now parse.

`src/spyceman/hosts/Cassini/_AS_FLOWN_CKS.py` uses `KTuple(...)` 104 times and no longer
imports it. Every sibling table — `_NAIF_LSKS.py`, `_DE_SPKS.py`, `_TOUR_SPKS_V3.py` and
the rest — still opens with `from spyceman.kernelfile import KTuple`; this one does not.

```text
NameError: name 'KTuple' is not defined
KTuple referenced 104 times; "import KTuple" present: False
```

It is the only generated table missing the import. Since `ktupler.py` was deleted in the
same revision (§1.7), the file cannot simply be regenerated.

### 1.4 Three debug `print()` statements left in the source

> **Fixed 2026-08-16.** All three removed.

- `src/spyceman/_spicefunc.py:365` — `print(33333, known)`, inside `_spicefunc()`, so it
  fires once per generated kernel function at import time and dumps the entire known-file
  table to stdout.
- `src/spyceman/_kernelinfo.py:459` — `print(11111, self)`, the first statement of the
  `naif_ids` property, which is on the hottest path in the library.
- `src/spyceman/solarsystem/General.py:32` — `print(22222)` at module scope.

All three are visible in the traceback from `import spyceman` today.

### 1.5 `is_basename()` no longer returns a bool

> **Fixed 2026-08-16.** The `bool()` wrapper was restored.

`src/spyceman/_utils.py`

```python
    return isinstance(basename, str) and _BASENAME_REGEX.match(basename)
```

The previous form wrapped the match in `bool()`. It now returns an `re.Match` object:

```text
is_basename("naif0012.tls") -> <re.Match object; span=(0, 12), match='naif0012.tls'>
type: Match | is True: False
```

The docstring immediately above states `bool: True if the string could be a SPICE kernel
file basename.` Every current caller uses the result in a boolean context, so nothing
breaks today, but the function no longer honors its contract, and the returned object
carries a reference to the input string.

### 1.6 `_get_spicepath()` inherits a bug and drops a documented feature

> **Fixed 2026-08-17.** `_get_spicepath()` takes a `missing` option restoring the three
> behaviors `initialize()` offered: `'ignore'` returns an empty list, `'warn'` issues a
> `UserWarning` once per session and returns an empty list, and `'error'` raises
> `RuntimeError`. Anything else raises `ValueError`. `walk()` passes the option through
> and defaults to `'warn'`, so a user with no SPICEPATH set gets a warning rather than a
> hard failure, as before. Covered by
> `tests/test_import.py::test_walk_without_spicepath_is_not_fatal`.


`src/spyceman/_localfiles.py:54-62`. The old `initialize(option='warn')` offered three
behaviors for a missing `SPICEPATH` — ignore, warn once, or raise. The replacement always
raises:

```python
def _get_spicepath():
    if 'SPICEPATH' in os.environ:
        return ':'.split(os.environ['SPICEPATH'])
    raise RuntimeError('missing environment variable "SPICEPATH"')
```

It also carries the reversed-arguments bug across unchanged (§9.1). And because
`walk()` now calls it whenever it is invoked with no directories, a user with no
`SPICEPATH` set gets a hard `RuntimeError` from what used to be a warning.

### 1.7 `ktupler.py` was deleted, but its outputs and references remain

> **Partly resolved 2026-08-16.** The tool was not deleted; it moved to
> `programs/ktupler.py`. `CLAUDE.md` and the `pyproject.toml` comment now point there.
> Still open: `programs/` is outside the packaged tree and outside every check the CI
> runs, so the generator is now unlinted and untested, and its own banner comment still
> reads `spyceman/ktupler.py`.

The tool that generates the `_UPPERCASE.py` KTuple tables is gone. Still referring to it:

- `pyproject.toml:115` — the ruff `exclude` comment: *"Machine-generated KTuple tables
  emitted by src/spyceman/ktupler.py."*
- `CLAUDE.md:94` — *"Regenerate with `python src/spyceman/ktupler.py`; do not hand-edit."*

Thirteen thousand lines of generated data now have no documented generator. If the tool
moved to another repository, say so in `CLAUDE.md`; if it was retired, the tables are
hand-maintained from now on and that should be recorded.

---

## 2. Previous findings now closed

Worth recording, so that this list is not re-reported:

- **`_downloads.py` parses.** The unterminated docstring, the missing `)` on the
  `SPICE-DOWNLOADS` line, and the missing `:` on the `else` are all fixed, and
  `import datetime` was added, closing the `NameError` in `retrieve_online_file()`.
- **`_KernelInfo.match()` returns its result.** It previously computed `basenames` and
  fell off the end returning `None`.
- **`hosts/_utils.py` exists.** `Cassini/spk.py` imported this module when it was not
  present; it now exists and `_intersect_basenames()` has `KernelFile` in scope, closing
  two undefined-name errors.
- **`KernelFile.__init__` and `must_exist()` take keyword-only options**, which prevents a
  basename from being silently accepted as `exists`.
- **The stray `00` at the top of `__init__.py`** is gone.

---

## 3. Where the import chain stops today

> **Resolved 2026-08-16. `import spyceman` now succeeds.**
>
> Thirteen fixes were needed to get there, in this order: §1.1, §1.2, §1.3, §1.4,
> §1.5, §4.2, §6.6, §6.5, §8.3, §8.2, §8.10, §8.1, §8.7, §6.7, §4.5, §8.11(3),
> §7.11. The package now builds every generated kernel function, selects real
> kernels through `func_template()`, and constructs its `default` Recipe holding
> `naif0012.tls` and `pck00011.tpc`.
>
> **`Recipe.furnish()` now works too, against the real SPICE toolkit.** Walking it
> took thirteen further fixes: §6.2, §6.3, §6.8, §6.15, §6.16, §6.17, §6.19, §6.20,
> §6.21, §7.3, §7.8, §7.14, and §7.15 -- four of which (§6.20, §6.21, §7.14, §7.15)
> were not in this review, because nothing had ever called `furnish()`. The README
> workflow runs end to end: two Recipes constructed, furnished over a time range,
> switched between with `select()`, queried with `used()`, and unloaded, with the
> SPICE kernel count moving as it should.
>
> **The `Rule` engine works too.** §5.1, §5.4, §5.5, and §5.12 are fixed, and rules
> now extract release dates, time ranges, versions -- including hierarchical ones --
> and derived family names from basenames, verified across all thirty documented
> date tags. Still untouched by any execution: the rest of §5 (§5.2, §5.3, and
> **All twelve findings in §5 are now fixed.** The `Rule` engine compiles its tags,
> matches basenames, extracts release dates, time ranges, versions, families and
> arbitrary properties, and scopes rules correctly by file extension. Still
> **All of §9 and §10 are now fixed as well.** `SPICEPATH` discovery,
> duplicate-basename detection, metakernel recognition, fancy-index parsing, and the
> download and label-retrieval paths all work, and `spyceman.hosts.Cassini` and
> `spyceman.hosts.Voyager` both import for the first time -- which took six further
> fixes that no review could have contained, because nothing had ever executed those
> modules. See §10.6 and §10.7.
>
> §6.1 and §7.4 have since been fixed as well. The Voyager and Cassini kernel
> functions now run: `_planet_spk()` returns a KernelSet for the flybys that
> happened and None for the two that did not.
>
> Everything below is the state at the time of the review, kept as the record.

`import spyceman` reached `_kernelinfo.py:547` at the time of this review [confirmed]:

```text
  File "src/spyceman/__init__.py", line 12, in <module>
    from spyceman.recipe      import Recipe
  File "src/spyceman/recipe.py", line 12, in <module>
    from spyceman.solarsystem import General
  File "src/spyceman/solarsystem/General.py", line 33, in <module>
    lsk = _spicefunc('lsk',
  File "src/spyceman/_spicefunc.py", line 366, in _spicefunc
    KernelFile.set_info(known)
  File "src/spyceman/kernelfile.py", line 221, in set_info
    kernel.naif_ids = item.naif_ids
  File "src/spyceman/_kernelinfo.py", line 547, in naif_ids
    self._naif_ids_as_found = self.naif_ids_as_found | ids
TypeError: unsupported operand type(s) for |: 'NoneType' and 'set'
```

Behind it, in order, sit §1.1, §1.2, and §1.3 — each of which is also fatal at module
scope. Fixing §4.2 alone will not produce a working import.

---

## 4. `_KernelInfo`

### 4.1 Three writes to a misspelled attribute — **critical**

> **Fixed 2026-08-16.** All three assignments now name `_naif_ids_as_found` and
> `_naif_ids_wo_aliases`. The junk attributes are gone, so `naif_ids_as_found` returns a
> set rather than `None` and `time` can iterate it.


`src/spyceman/_kernelinfo.py:466, 467, 472`

```python
466            self._naif_as_found = set()          # attribute is _naif_ids_as_found
467            self._naif_wo_aliases = set()        # attribute is _naif_ids_wo_aliases
472            self._naif_as_found = self._rule_values['naif_ids']
```

`__init__` declares `_naif_ids_as_found` and `_naif_ids_wo_aliases` (lines 70–71). These
three assignments create two junk attributes that nothing reads and leave the declared
ones at `None`.

The consequence is a silent `None`, not an exception. `naif_ids_as_found` (line 602) tests
`if self._naif_ids_as_found is None`, calls `self.naif_ids`, which returns early at line
460 because `_naif_ids` *was* set — and then returns `None`.

Line 472 is on the hot path: it is the branch taken whenever the basename rules supply the
IDs, which is the normal case for every managed kernel family. `time` iterates that value
at line 716, so computing the time range of an SPK raises `TypeError: 'NoneType' object is
not iterable`.

### 4.2 The `naif_ids` setter is the current import blocker — **critical** [confirmed]

> **Fixed 2026-08-16.** The setter now normalizes `ids` to a set once and assigns
> `_naif_ids_as_found` directly, rather than reading it back through a property that
> could only return `None`. The six lines of dead code are gone, and all three
> derived attributes are populated on every path. `import spyceman` now clears
> `set_info()` and stops at §6.6 instead.
>
> Still open in this section: `add_naif_ids()` and `remove_naif_ids()` continue to
> read `self.naif_ids_as_found`, which returns `None` for an LSK or a rule-derived
> kernel because of the misspellings in §4.1. Neither is on the import path.

`src/spyceman/_kernelinfo.py:540-550`

```python
540        if isinstance(ids, numbers.Integral):
541            self._naif_ids = {ids}
542        elif not ids:
543            self._naif_ids = set()
544        else:
545            self._naif_ids = set(ids)
546
547        self._naif_ids_as_found = self.naif_ids_as_found | ids
548        self._naif_ids = naif_ids_with_aliases(ids)
```

Line 547 was changed this revision from `self._naif_ids_as_found |= ids`. The new form is
worse, because it now routes through the *property*, and the property cannot help: it sees
`_naif_ids_as_found is None`, calls `self.naif_ids`, which returns immediately at line 460
because lines 541–545 just set `_naif_ids` — so `_naif_ids_as_found` is never populated and
the property returns `None`. Hence `None | ids`.

Two further problems in the same nine lines. `ids` may still be a bare `int` at line 547
(line 540 exists precisely to handle that case), so `set | int` would raise even with a
non-`None` left operand. And lines 540–545 carefully compute `self._naif_ids` only for line
548 to overwrite it unconditionally — six lines of dead code.

`add_naif_ids` (line 560) has the identical `None | ids` hazard.

### 4.3 `_manual_defs.append(tuple + set)` raises `TypeError`

> **Fixed 2026-08-16.** Both sites now append `+ tuple(ids)`.


`src/spyceman/_kernelinfo.py:563` and `:576` — `('add_naif_ids',) + ids` where `ids` was
just converted to a `set`. `tuple + set` is unsupported; it needs `+ tuple(ids)`.

### 4.4 `naif_ids` assigns an empty dict where a set is required

> **Fixed 2026-08-16.** The fallback is `set()`, so it flows through
> `naif_ids_with_aliases()` as the empty set it was meant to be.


`src/spyceman/_kernelinfo.py:497-500`

```python
        elif self.is_text:
            naif_ids = self._naif_ids_from_text_kernel()
            if not naif_ids:
                naif_ids = {}
```

`{}` is a dict. It flows into `naif_ids_with_aliases()` at line 528, which tests
`isinstance(ids, (set, list, tuple))`, finds a dict is none of those, and wraps it as
`{ids}` → `TypeError: unhashable type: 'dict'`.

### 4.5 Two properties read `self._rules_values`, which does not exist

> **Fixed 2026-08-16.** Both sites now read `_rule_values`. `source` and `dest` return
> their defaults (`[]` and `""`) instead of raising. Fixed after §6.7, per the ordering
> constraint in §8.11, so that no import ever reached for the network.

`src/spyceman/_kernelinfo.py:1006` and `:1033`. The attribute is `_rule_values`, singular.
Both `source` and `dest` raise `AttributeError` — and these are exactly the two properties
the download machinery consults (`kernelfile.py:153-155`).

### 4.6 `time` tests a tuple for membership in a string-keyed dict

> **Fixed 2026-08-16.** The test is now `elif 'time' in self._default_values`, so
> default-rule time ranges are consulted.


`src/spyceman/_kernelinfo.py:700-704`

```python
        time = (None, None)
        if 'time' in self._rule_values:
            time = self._rule_values['time']
        elif time in self._default_values:
```

The `elif` should read `elif 'time' in self._default_values`. As written it asks whether
the tuple `(None, None)` is a key of a dictionary keyed by strings — always `False`.
Default-rule time ranges are never used.

### 4.7 `time` calls the constructor instead of `lookup()`

> **Fixed 2026-08-16.** Now calls `_KernelInfo.lookup(basename).time`, which returns the
> existing record instead of raising on a basename already registered.


`src/spyceman/_kernelinfo.py:754` — `_KernelInfo(basename).time`. `__init__` raises
`ValueError('_KernelInfo already defined for ...')` for any basename already registered,
which for a file referenced by a metakernel it will be. Compare line 495, which indexes
`KERNELINFO` directly, and the `lookup()` static method that exists for this purpose.

### 4.8 `naif_ids` can raise `KeyError` on a legitimately known file

> **Fixed 2026-08-16.** The lookup goes through `_KernelInfo.lookup()`, which creates
> the record if only `ABSPATHS` knows the file. The underlying registry split is
> addressed in §11.2.


`src/spyceman/_kernelinfo.py:492-495` guards on `ABSPATHS` but indexes `KERNELINFO`. The
two registries are not kept in step: `_localfiles.use_path()` (lines 150–151) registers a
discovered file in `ABSPATHS` and `BASENAMES_BY_KTYPE` but never constructs a
`_KernelInfo`. A file found by walking the filesystem is therefore in one and absent from
the other. See §11.2.

### 4.9 `release_date` can raise `UnboundLocalError`

> **Fixed 2026-08-16.** `timestamp` and `timestamp_date` are computed once, before
> either branch, since both steps need them. With `_USE_INTERNAL_DATES` false and
> `_USE_TIMESTAMP_DATES` true, step 6 now has its value.


`src/spyceman/_kernelinfo.py:857-884`. `timestamp_date` is assigned only inside
`if _KernelInfo._USE_INTERNAL_DATES:` (line 872) but read at line 884 inside
`if _KernelInfo._USE_TIMESTAMP_DATES:`. With the first flag false and the second true, line
884 raises. Both are class-level switches, so this is reachable by configuration alone —
and it was previously reachable from `ktupler.py`'s `--timestamps` flag, which set exactly
that combination.

### 4.10 `properties[name] = value` raises `AttributeError`

> **Fixed 2026-08-16.** `_local_dict` takes its owning `_KernelInfo` and stores it as
> `_owner`; `__setitem__` and `__delitem__` delegate to `_owner.add_property()` and
> `_owner.remove_property()`. The syntax the docstrings advertise now works.


`src/spyceman/_kernelinfo.py:1053-1071`. `_local_dict.__setitem__` calls
`self.add_property(key, value)`, but `self` is the dict, which has no such method and no
reference to its owning `_KernelInfo`. The docstrings of `add_property` and
`remove_property` advertise `self.properties[name] = value` as the equivalent syntax; that
syntax raises.

---

## 5. The `Rule` engine

`rule.py` is byte-for-byte unchanged this revision. It converts a basename into a release
date, time range, version, family, and properties, and `_KernelInfo` consults it for nearly
every attribute it exposes. It does not work.

### 5.1 `_date_regex()` discards every replacement — **critical** [confirmed]

> **Fixed 2026-08-16.** Each `str.replace()` result is now assigned. Verified against
> all thirty date tags documented in `Rule.__init__`, each matched against the
> example given for it in that same docstring: 30/30. Invalid tags are still
> rejected, and the generated expression still refuses month 13, day 32, year 1822,
> and a truncated date.
>
> `Rule(r"cas_v(YYYYMMDD)\.tsc")` now compiles to
> `cas_v((?:19[7-9]\d|20\d\d)(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01]))\.tsc` and
> matches `cas_v20221201.tsc`, where before it matched only the literal string
> `cas_vYYYYMMDD.tsc`.
>
> **Correction to the note below:** it claimed the existing substitution order "puts
> `MM` before `MON`, which will corrupt `MON` tags". That is wrong. No valid tag
> contains both, and none of the replacement expressions contains a tag substring, so
> no substitution can be re-matched by a later one. The order needed no change; only
> the assignments were missing.
>
> This unblocks the two defects immediately behind it, both of which now fire on
> every date-bearing rule: §5.4 (`AttributeError: 'Rule' object has no attribute
> 'date_group'`) for a one-date rule, and §5.5 for a two-date rule, where the
> malformed `2004-01-1` reaches julian as
> `JulianParseException: unrecognized ISO date format`.

`src/spyceman/rule.py:96-104`

```python
    pattern = tag
    pattern.replace('YYYY', _YYYY)
    pattern.replace('YY',   _YY)
    pattern.replace('MM',   _MM)
    ...
    return pattern
```

`str.replace` returns a new string; none of the six results is assigned, so the function
returns the tag itself. Lifting it verbatim out of the current source:

```text
_date_regex("YYYYMMDD") -> 'YYYYMMDD'
matches "20221201"? False
```

Every date tag in every rule compiles to a literal match on the letters of the tag. A rule
written `r'cas_v(YYYYMMDD)\.tsc'` matches only the literal string `cas_vYYYYMMDD.tsc`.
Release-date extraction, time-range extraction, and family naming are disabled for every
rule that uses a date tag — which is most of them across `hosts/` and `solarsystem/`.

**Fix**: assign each result. `'YYYY'` must be substituted before `'YY'`. (The claim
that the order also corrupts `MON` tags is withdrawn -- see the status note above.)

### 5.2 `Rule._RULES` aliases every extension to one shared list — **critical** [confirmed]

> **Fixed 2026-08-16.** The template dict and its shallow copy are gone; each
> extension now builds its own six lists in a nested comprehension. There are 78
> distinct list objects for 13 extensions x 6 field counts, where before there were
> six in total. `rules_by_count` no longer leaks as a public class attribute.
>
> Verified: registering `probe_v(NN)\.bsp` changes the counts for `.bsp` alone, and
> `apply_all()` returns its version for `probe_v01.bsp` but `{}` for `probe_v01.bc`
> and `probe_v01.tls`. A rule whose extension cannot be inferred still registers
> under `""` and still applies to every extension.
>
> This closes the correctness risk noted below -- an SPK rule could previously claim
> a CK basename -- and cuts the work `apply_all()` does per basename from every rule
> in the package to the ones for that extension plus the extension-less ones.

`src/spyceman/rule.py:257-265`

```python
    rules_by_count = {0:[], 1:[], 2:[], 3:[], 4:[], 5:[]}
    _RULES = {}
    for ext in _EXTENSIONS:
        _RULES[ext] = rules_by_count.copy()
```

`dict.copy()` is shallow, so every per-extension dictionary holds references to the same
six lists:

```text
_RULES[".tf"][1] after registering a .bsp rule -> ['bsp-only rule']
```

The per-extension indexing — the entire point of the structure, per the comment above it —
is defeated. Once §5.1 is fixed this becomes a correctness problem rather than merely a
performance one, since an SPK rule can claim a CK basename. `rules_by_count` is also left
bound as a public class attribute.

### 5.3 `Rule.apply_all()` applies no rules when the extension is unknown

> **Fixed 2026-08-16.** `key_list = ('',)` -- one comma. `apply_all()` now returns
> the extension-less rules' results for `.xyz`, `.dat`, and `.nosuchext` basenames,
> where it previously returned `{}`. Recognized extensions are unaffected, and an
> unrecognized one still sees only the `""` bucket: a `.bsp`-only rule does not
> apply to `probe_v01.xyz`.

`src/spyceman/rule.py:573` — `key_list = ('')` is the empty *string*, not a one-element
tuple, so `for key in key_list` iterates zero times. For any basename whose extension is
not in `_EXTENSIONS`, no rules are applied at all — including the extension-agnostic rules
registered under `''`, which is exactly what this branch exists to serve. Needs `('',)`.

### 5.4 `Rule.match()` reads two attributes that do not exist — **critical**

> **Fixed 2026-08-16.** Both now read `_date_group` and `_version_type`. A one-date
> rule returns `{'release_date': '2022-12-01', 'family': 'Cassini-SCLK'}`; a version
> tag returns `12`, and a hierarchical `kernel_v(N+).(N).(N)` returns `(10, 2, 3)`,
> which is the example in the constructor docstring.

`src/spyceman/rule.py:470` uses `self.date_group`; the attribute is `self._date_group`
(line 382). Line 490 uses `self.version_type`; the attribute is `self._version_type`. The
first fires for any rule with a release-date group, the second for any rule with exactly
one version group.

### 5.5 `_date_iso()` emits malformed ISO dates

> **Fixed 2026-08-16.** Now `f'{year:04d}-{mm}-{dd:02d}'`. All thirty documented date
> tags produce the correct date and parse cleanly through julian: 30/30. See §5.12 for
> a second defect in the same function, found while verifying this one.

`src/spyceman/rule.py:619-621` — `dd` is an `int`, `mm` a string, so
`f'{year}-{mm}-{dd}'` yields `2022-12-1` for single-digit days. Release dates are compared
as strings downstream (`kernelfile.py:820-823`), so this sorts wrongly rather than raising.

### 5.6 `_default_dates_from_basename()` raises on any date containing a month

> **Fixed 2026-08-16.** The month is converted to an int on the string branch --
> `int(_MON_DICT.get(m, m))` turns both `"dec"` and `"12"` into `12` -- so both
> branches reach the same formatting, now `f'{y:04d}-{m:02d}-{d:02d}'`.
>
> The default rule now reads dates out of a basename in every format tried:
> `cas_20221201.tsc`, `cas_2022-12-01.tsc`, `cas_2022_Dec_01.tsc`,
> `cas_01Dec2022.tsc`, and the two-date `ck_20040105_20050101.bc` all yield dates
> that parse cleanly through julian, including the single-digit month and day cases
> this finding was about.
>
> Fixing it makes §5.7 plainly visible: `sclk_2022305.tsc` gets the family
> `sclk_YYYYDOY.tsc`, but `cas_20221201.tsc` gets `cas_20221201.tsc` -- unchanged.
> Day-of-year is the last of the three split options, so only its replacements
> survive. And because `_DefaultRule.apply()` reports a family only when it differs
> from the basename, a date-bearing basename now gets a date but no family at all:
> `_DefaultRule.apply("cas_20221201.tsc")` returns `{'date': '2022-12-01'}`.

`src/spyceman/rule.py:771-779` — in the branch where `m` is a month string,
`f'{y}-{m:02d}-{d:02}'` raises `ValueError: Unknown format code 'd' for object of type
'str'`. Only the day-of-year branch, where `julian` supplies ints, survives. `YYYYMMDD`
and `YYYY-MON-DD` are far more common in SPICE basenames than `YYYYDOY`.

### 5.7 `_default_dates_from_basename()` discards all but the last split option's tagging

> **Fixed 2026-08-16.** The family name is now built once, after
> filtering, from the surviving captures -- working backwards through the basename so
> the earlier indices stay valid -- rather than being rebuilt inside the loop. Each
> split option still runs against the original basename, so the captures stay keyed by
> an index that means the same thing across all three.
>
> `mix_20040105_2005305.bc` now yields `mix_YYYYMMDD_YYYYDOY.bc`, with two different
> split options each contributing a tag. Before, only the last option's replacements
> survived, so a `YYYYMMDD` name kept its digits and got no family at all.
>
> One further defect was fixed alongside it, in `_DefaultRule.apply()`: it called
> `_default_version_from_basename(basename)`, restarting from the untagged basename and
> so discarding the date-tagged family. It now chains from `family`, and a name
> carrying both a date and a version keeps a tag for each.

`src/spyceman/rule.py:717-740`. `regex.split(basename)` runs against the original basename
on each of the three iterations, and `family = ''.join(parts)` sits inside the loop, so
each pass overwrites the previous pass's family. The comment at line 737 describes an
intent the code does not implement.

### 5.8 `_default_dates_from_basename()` can dereference `None`

> **Fixed 2026-08-16.** A substring that splits but fails to parse
> is skipped. `cas_2022-12_01.tsc` and `cas_2022_12-01.tsc`, whose two separators
> differ, now return cleanly with no dates instead of raising `AttributeError` on
> `None.groupdict()`.

`src/spyceman/rule.py:723-724`. The split patterns allow a date's two separators to
differ; the parse patterns require them to match via `(?P=x)`. A basename containing
`2022-12_01` splits successfully, fails to parse, and line 724 calls `.groupdict()` on
`None`.

### 5.9 `_DefaultRule` and `Rule` disagree on the release-date key

> **Fixed 2026-08-16.** Standardized on `release_date`, the key
> `Rule.match()` already produced and the one `_KernelInfo.properties` already knew to
> exclude from the property dictionary. `_DefaultRule.apply()` now returns it, and both
> lookups in `_KernelInfo.release_date` were corrected -- the first had been checking
> for the default rule's key in the explicit rules' dictionary.
>
> `KernelFile("probe_20221201.tsc").release_date` is now `'2022-12-01'`, read from the
> basename, where before it fell through to the file timestamp.

`_DefaultRule.apply()` returns the date under `'date'` (line 632); `Rule.match()` returns
it under `'release_date'` (line 471). `_KernelInfo.release_date` then checks
`'date' in self._rule_values` (line 824) — the *rule* dictionary with the *default rule's*
key. Rule-derived release dates are never found. That `_KernelInfo.properties` (line 1089)
explicitly filters `'release_date'` out shows the author knew which key `Rule` produces.

### 5.10 `Rule.match()` can silently reuse a stale capture

> **Fixed 2026-08-16.** Captured and literal properties are
> handled in separate branches, so a captured substring can no longer leak from one
> property to the next, and the blanket `except Exception: pass` is gone. An optional
> group that did not participate is skipped rather than crashed on.
>
> Verified across all four property kinds: a function transform, a dictionary lookup
> including a miss, a verbatim capture, and a literal. A literal `ctype=3` beside a
> captured `origin` now stays `3` instead of picking up the neighbouring capture. A
> transform that raises now surfaces the error rather than silently dropping the
> property.

`src/spyceman/rule.py:531-549`. `capture` is assigned only when `name` is in
`self._captures`. For a non-capture property reaching the `value is None` branch, `capture`
either is unbound or still holds the value captured for a *previous* property in the same
loop, which is then stored under the wrong name. The bare `except Exception: pass` at line
548 hides both outcomes and every other error in the block.

### 5.11 `_interpret_tags()` miscounts groups for some non-capturing constructs

> **Fixed 2026-08-16.** Group counting is now done by
> construct rather than by a list of prefixes: a group captures only if it is a plain
> `(...)` or a named `(?P<name>...)`. A new `_count_capturing_groups()` helper counts
> groups at any depth, skipping escaped parentheses and parentheses inside a character
> class.
>
> The defect was broader than this finding described. Beyond the missing `(?=...)` and
> inline-flag cases, `_split_balanced_parens()` does not recurse, so **any capturing
> group nested inside a non-capturing one was invisible**: in
> `x(?:_(?P<tag>[a-z]+))?_v(NN)\.bc` the version tag was read from the wrong group and
> `int()` was applied to the wrong text. The new counter was checked against Python's
> own `re.compile(...).groups` across fifteen fragments -- plain, named, non-capturing,
> backreference, both lookaheads, both lookbehinds, inline flags, comments, nested,
> escaped, and character-class parentheses -- and agrees on every one.

`src/spyceman/rule.py:150` omits `(?=...)` and inline flag groups such as `(?i)` from its
list of non-capturing prefixes, so `group_index` is incremented for them and every
subsequent tag is bound to the wrong group number.

---

### 5.12 The day-of-year branch calls a julian function that does not exist — **critical** [confirmed]

> **Found and fixed 2026-08-16**, while verifying §5.5. Not in the original draft: with
> §5.1 unfixed no date tag ever matched, so no branch of `_date_iso()` was ever reached.

`_date_iso()` ended its day-of-year branch with:

```python
            day = julian.day_from_yd(year, int(string[i:i+3]))
            return julian.iso_from_day(day)
```

`julian` has no `iso_from_day`:

```text
AttributeError: module 'julian' has no attribute 'iso_from_day'. Did you mean: 'iso_from_tai'?
```

Six of the thirty documented date tags -- `YYYYDOY`, `YYYY_DOY`, `YYYY-DOY`, `YYDOY`,
`YY_DOY`, `YY-DOY` -- go through this branch, so every day-of-year rule in the package
raised. Day-of-year naming is common in SPICE kernels; `Cassini/ck.py` alone registers
several `(YYDOY)` rules.

**Fix**: `julian.format_day(day)`, which exists, returns `"yyyy-mm-dd"`, and is already
what `_kernelinfo.py` uses for the same purpose.

Prompted by this, every `julian.X` call in the package was checked against the installed
module. This was the only one missing; the other nine names all resolve.

---

## 6. `Kernel` and `KernelFile`

`kernel.py` is byte-for-byte unchanged this revision. `kernelfile.py` changed only in its
imports and in making two parameter lists keyword-only.

### 6.1 `Kernel` is unhashable but is stored in sets throughout — **critical** [confirmed]

> **Fixed 2026-08-16.** `Kernel.__hash__` is defined in terms of a `_hash_key()`
> method that subclasses refine.
>
> A hash cannot simply mirror `__eq__` here, because `__eq__` compares the whole
> instance dictionary -- mutable, and holding lazily cached values. The default
> `_hash_key()` is the class name alone, which is always consistent with `__eq__`
> and merely puts every instance of a class in one bucket. `KernelFile` overrides it
> with its basename, which is fixed at construction and, since every other attribute
> lives in the global `_KernelInfo` keyed by that basename, fully identifies it.
> That is the subclass that actually goes into large sets.
>
> Verified: the invariant holds -- equal objects hash equally, and unequal ones are
> free to differ; a set of three KernelFiles with two identical collapses to two;
> membership by an equal-but-distinct object succeeds; `exclude()` and `require()`
> both populate their sets; and every subclass is hashable.
>
> The usual caveat for a mutable set member applies and is documented on the method:
> a Kernel mutated after it enters a set may not be found there again.

`src/spyceman/kernel.py:116` defines `__eq__` with no `__hash__`, so Python sets
`__hash__ = None`:

```text
__hash__ is None
set([kernel]) ->  TypeError: unhashable type
```

`exclusions`, `prerequisites`, `postrequisites`, and `corequisites` are all sets, and
`_add_to_set` adds Kernel objects to them directly (lines 578, 580). `KernelFile.reduce`
builds `set(coverage.values())` of KernelFiles (line 726) and `filter_basenames` builds
`set(kfiles)` (line 960).

Because `__eq__` compares `__dict__`, a hash consistent with it cannot be derived from the
same mutable state. The sensible resolution is identity-based hashing, or hashing on
`(type, tuple(basenames))` with a documented rule that a Kernel must not be mutated after
entering a set.

### 6.2 `_FURNISHED_BASENAMES` is a dict of dicts but used as a dict of lists — **critical** [confirmed]

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. Now `{key: [] for key in _KTYPES}`,
> matching both the comment above it and every use of it.

`src/spyceman/kernel.py:17`

```python
_FURNISHED_BASENAMES = {key:{} for key in _KTYPES}
```

The comment directly above says "ordered list of basenames currently furnished". The code
uses `.index()` (line 769), `.append()` (line 773), `.pop(loc)` (line 754) and
`enumerate()` (line 743) on it:

```text
type: dict | has .append: False | has .index: False
```

`dict.pop` exists and takes a key, so that call will not even fail loudly. Needs
`{key: [] for key in _KTYPES}`.

### 6.3 `Kernel.furnish()` furnishes the wrong object, or raises `NameError` — **critical**

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. Line 692 now calls `self._furnish_for(...)`.
> Observed live before the fix: furnishing the `default` Recipe called `must_exist()`
> on `pck00009.tpc`, an *excluded* kernel -- the last value of the exclusions loop.

`src/spyceman/kernel.py:683-691`

```python
683        for kernel in self.prerequisites:
684            kernel = Kernel.as_kernel(kernel)
685            loc, minloc = kernel.furnish(...)
686            minloc = max(minloc, loc)
...
690        maxloc = kernel._furnish_for(tmin=tmin, tmax=tmax, ids=ids, minloc=minloc,
```

Line 690 should be `self._furnish_for(...)`; the comment above it says so. As written it
uses `kernel`, the leaked loop variable. With no prerequisites, `kernel` is either unbound
or — if the exclusions loop at line 677 ran — the last *excluded* kernel, which is then
furnished. This is the central method of the library.

### 6.4 `furnish()` returns a scalar but is unpacked as a pair

> **Fixed 2026-08-16.** `furnish()` now returns `(maxloc, refloc)` when a `refloc` was
> supplied and the bare `maxloc` otherwise, matching what its recursive calls unpack and
> what `_furnish_for()` already did.


`furnish()` always returns `maxloc` (line 706), yet its recursive calls unpack two values
at lines 685 and 696. `_furnish_for` does implement the two-value contract (lines 811–814),
but `furnish` accepts `refloc` and never propagates it.

### 6.5 `KernelFile.basenames` recurses infinitely — **critical** [confirmed]

> **Fixed 2026-08-16.** Now returns `[self.basename]`, using the property added in
> §6.6 so the basename has a single source of truth. Fixing it exposed §6.19, which
> this recursion had been masking.

`src/spyceman/kernelfile.py:253` — `return [self.basenames]`, inside the `basenames`
property. It should be `[self._basename]`. Since `basenames` is the property every
`Kernel` method iterates, this alone makes `KernelFile` unusable.

### 6.6 `KernelFile.basename` does not exist — **critical** [confirmed]

> **Fixed 2026-08-16.** Added as a property returning `self._basename`, alongside
> `basenames`. `KernelFile.name`, `.ext`, and the "alpha" and callable sort keys all
> work again; `import spyceman` now clears the sort in `_spicefunc()` and stops at
> §8.3. Note that §6.5 is untouched, so `basenames` still recurses.

`kernelfile.py:264` implements `name` as `return self.basename`, but no `basename`
property is defined on `KernelFile` or on `Kernel`. The attribute is `_basename`.

```text
"def basename(" present: False
".basename" referenced in kernel.py + kernelfile.py: 22 times
```

It is also used in `metakernel.py:63` and `_spicefunc.py:239`. The `KernelFile` class
docstring documents the whole `k.*` property family and omits the one used most. Adding it
is a one-line change that unblocks a large fraction of the package.

### 6.7 `KernelFile(basename, exists=True)` has its logic inverted — **critical**

> **Fixed 2026-08-16.** Collapsed to a single assertion:
>
> ```python
>         if exists and basename not in _KernelInfo.ABSPATHS:
>             raise FileNotFoundError('kernel file not found: ' + repr(basename))
> ```
>
> The `must_exist()` call was dropped from the constructor rather than moved to the
> other branch. Two pieces of evidence decided that: `exists=True` has exactly one
> caller, `_add_to_set()`, which wants an assertion and not a download; and
> `must_exist()` is already invoked explicitly at `kernel.py:746`, inside
> `_furnish_for()`, which is where fetching actually belongs. The parameter is named
> for a state, not an action. The docstring was corrected to match -- it had claimed
> "downloading it if necessary", which was an inference from the buggy code.
>
> Verified with `socket.connect` patched to raise: `exists=True` raises for a missing
> file, succeeds for a registered one, `exists=False` is unaffected, and no network
> access is attempted at any point.

`src/spyceman/kernelfile.py:122-126`

```python
        if exists:
            if basename not in _KernelInfo.ABSPATHS:
                self.must_exist()
            else:
                raise FileNotFoundError('kernel file not found: ' + repr(basename))
```

A file that *is* present raises `FileNotFoundError`; a file that is *absent* triggers a
download. The branches are swapped, and the message describes the opposite of the
condition that produces it. `Kernel._add_to_set` (line 548) uses this constructor.

### 6.8 `set_info()` is called with the wrong signature and mutates the wrong object

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. `**properties` at the call site, and
> `kernel.add_property(...)` rather than `info.add_property(...)` inside the loop.

`kernelfile.py:120` calls `KernelFile.set_info([self], properties)`, passing the dict
positionally to a function declared `set_info(info, **properties)`. `TypeError`.

`kernelfile.py:229` then calls `info.add_property(name, value)` inside the per-item loop,
where `info` is the *list* being iterated. The same mistake appears again at line 503.

Line 227, `KernelFile.__dict__[name].fset(kernel, value)`, additionally assumes every
matching class attribute is a settable property.

### 6.9 `release_date` setter falls through its own guard

> **Fixed 2026-08-16.** The empty-value branch assigns `''` and returns, so
> `julian.day_from_string()` is no longer handed the empty value it just rejected.


`src/spyceman/kernelfile.py:389-393` — the `if not value:` branch sets `''` and then, with
no `return`, calls `julian.day_from_string(value)` on the same empty value.

### 6.10 `KernelFile.checksum` delegates to a property that does not exist

> **Fixed 2026-08-16.** `checksum` calls `_file_checksum(self.abspath)` directly, which
> is the module-level function that was never wired up.


`kernelfile.py:580` returns `self._info.checksum`. `_KernelInfo` defines no `checksum`
property; `_localfiles._file_checksum()` is a module-level function never wired to it.

### 6.11 `reduce()` sets `tmin` when it means `tmax`

> **Fixed 2026-08-16.** The `else` branch assigns `tmax = BIGTIME`. Verified together
> with §6.12.


`src/spyceman/kernelfile.py:702-707` — in the `else` branch of the `tmax is None` test, the
assignment is `tmin = BIGTIME`. `tmax` stays `None`, and line 735 then calls
`portion.closed(tmin, tmax)` with a `None` bound.

### 6.12 `reduce()` maps an open-ended upper limit to the far past

> **Fixed 2026-08-16.** An unconstrained lower limit is `-BIGTIME` and an unconstrained
> upper limit is `+BIGTIME`, so `portion.closed()` receives a range that covers
> everything rather than one that inverts.


`src/spyceman/kernelfile.py:725-729` — `if t1 is None: t1 = -BIGTIME` should be
`+BIGTIME`. A kernel valid for all times becomes the degenerate interval
`[-1e99, -1e99]` and covers nothing.

### 6.13 `find_all()` has a copy-pasted branch that raises `KeyError`

> **Fixed 2026-08-16.** The extension is looked up only when it is a recognized one (`if
> ext in _EXTENSIONS`), falling back to the explicit `ktype` and then to every known
> basename. The copy-pasted branch that indexed `BASENAMES_BY_KTYPE` with an arbitrary
> suffix is gone.


`src/spyceman/kernelfile.py:1016-1020`

```python
        if ext in _EXTENSIONS:
            sources = _KernelInfo.BASENAMES_BY_KTYPE[_EXTENSIONS[ext]]
        elif ktype:
            sources = _KernelInfo.BASENAMES_BY_KTYPE[_EXTENSIONS[ext]]
```

The `elif` body is identical to the `if` body but is reached precisely when `ext` is *not*
in `_EXTENSIONS`, so `_EXTENSIONS[ext]` raises. It should be
`BASENAMES_BY_KTYPE[ktype]` — the only reason the `ktype` parameter exists.

### 6.14 `filter_basenames()` and `reduce()` crash on an empty list

> **Fixed 2026-08-16.** Both functions return early on an empty list rather than
> indexing `basenames[0]`.


Both index `basenames[0]` with no length check (lines 690 and 932). An empty candidate list
is the normal outcome of a restrictive filter. `filter_basenames` additionally does
`unfiltered.index(kfiles[-1])` at line 957 when `expand=True`, raising `IndexError`
whenever the filters removed everything — exactly the case `expand` exists to recover from.

### 6.15 `unload()` catches the wrong exception and reads the wrong attribute

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. `except ValueError` and `Kernel._VERBOSE`.
> `unload()` now removes the kernel from SPICE: the loaded count drops from 2 to 1.

`src/spyceman/kernel.py:853-860` — `list.index` raises `ValueError`, not `KeyError` (line
855; compare line 772, which gets it right in the sibling method), and `Kernel.VERBOSE`
(line 860) should be `Kernel._VERBOSE`.

### 6.16 `has_overlap()` calls a method that does not exist

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. Now calls `time_overlap()`.

`kernel.py:960` calls `self._time_overlap(...)`; the method is `time_overlap` (line 965).
It is on every path that selects kernels: `_furnish_for`, `unload`, `_used_for`, and
`filter_basenames`.

### 6.17 `time_overlap()` raises on unconstrained kernels

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. The limits are compared only when
> both are known; an unconstrained end cannot rule out an overlap.

`kernel.py:1005-1011`. When the kernel has `time == (None, None)` — LSKs, SCLKs, and
text PCKs, per `_kernelinfo.py:691` — and the query passes `tmin=tmax=None`, both `t0` and
`t1` stay `None` and line 1011 evaluates `None < None - dt`. This is the common case for
the very kernels the `default` Recipe furnishes.

### 6.18 Smaller defects in the same two files

> **Fixed 2026-08-16.** Every item in this list is now addressed: `id_overlap()` reads
> `naif_ids`; `_add_to_set()` wraps with `set()`; `_version_for_kernels()` goes through
> `Kernel.as_kernel()`; `_properties_for_kernels()` iterates a materialized list;
> `__copy__()` passes the class to `__new__`; the `version` setter calls
> `validate_version` from `_utils`; `family` no longer reads a `_name` that may be
> unset; both missing `f` prefixes are in place; and `refloc` is tested with `is not
> None` so index 0 is honored. `veto()` now detects a capture reference with the
> `_GROUP_REFERENCE` pattern rather than relying on `re.compile` to raise.


- `kernel.py:1035` — `id_overlap()` reads `kernel.ids`; the attribute is `naif_ids`.
- `kernel.py:571` — `_add_to_set()` computes `kernel.basenames & self.basenames`;
  `basenames` is a list. Line 557 in the same method correctly wraps with `set(...)`.
  **Fixed 2026-08-16**, as a prerequisite for §7.1: passing a Kernel object to
  `require()` reaches this line, so `KernelStack.prerequisites` could not be shown
  to work until it was wrapped.
- `kernel.py:1178` — `_version_for_kernels()` calls `k.version_as_set` on a basename
  string. Every sibling helper wraps with `Kernel.as_kernel(k)`.
- `kernel.py:1227` — `_properties_for_kernels()` deletes from `merged` while iterating
  `merged.items()`, raising `RuntimeError: dictionary changed size during iteration`.
- `kernel.py:112` — `__copy__()` calls `type(self).__new__()` with no class argument.
- `kernel.py:379` — the `version` setter calls `_KernelInfo._validate_version`, which does
  not exist; the function is `validate_version` in `_utils`.
- `kernel.py:393` — `self._family = self._family = self._name` reads `_name`, which the
  `name` property sets lazily, so `family` raises `AttributeError` on a Kernel whose `name`
  has not been accessed.
- `kernel.py:553` — `set(_KernelInfo.match(kernel))` is now correct, since `match()` was
  fixed this revision.
- `kernel.py:806` — `print('Spyceman:', kfile.basename, 'reloaded ({reason})')` is missing
  its `f` prefix; line 789, four lines earlier, has it.
- `kernel.py:773` — `if refloc and loc <= refloc` skips the adjustment when `refloc` is
  `0`, a legitimate index and the default in `unload()`.
- `kernelfile.py:184` — `raise FileNotFoundError('no identified source for
  "{self.basename}"')` is missing its `f` prefix.
- `kernelfile.py:1200-1214` — `veto()` compiles substitution templates with `subs=True`,
  but `_compile` only produces a template tuple when `re.compile` *raises*. A template
  containing `\1` compiles fine as a backreference, so the documented capture-reference
  feature never triggers.

---

### 6.19 `Kernel.as_kernel()` passes a parameter `KernelFile` does not accept — **critical** [confirmed]

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. The `download=True` argument was dropped.
> Constructing a Kernel is not the place to fetch anything; `_furnish_for()` calls
> `must_exist()` where that belongs, and `Kernel._DOWNLOADS` governs it there.
>
> **Found 2026-08-16**, while verifying the §6.5 fix. It was not in the original draft of
> this review: with `basenames` recursing, no call ever reached `as_kernel()` with a
> string, so the defect was unreachable and went unnoticed.

`src/spyceman/kernel.py:141`

```python
        return Kernel.KernelFile(kernel, download=True)
```

`KernelFile.__init__` is declared `(self, basename, *, exists=False, **properties)`. There
is no `download` parameter, so `download=True` is absorbed into `**properties` and treated
as the name of a custom property — which routes into `set_info()` and trips §6.8:

```text
as_kernel calls  : Kernel.KernelFile(kernel, download=True)
__init__ accepts : (self, basename, *, exists=False, **properties)
as_kernel("naif0012.tls") -> TypeError: KernelFile.set_info() takes 1 positional argument
                             but 2 were given
```

`as_kernel()` is the universal string-to-Kernel converter; `kernel.py` calls it in
`furnish()`, `unload()`, `used()`, `ktype`, and all six `_*_for_kernels()` helpers. Every
one of those raises for a basename argument. Passing a Kernel through is unaffected,
because that path returns early.

Two things need deciding here, not one. The immediate defect is the unknown keyword. But
the intent behind it also looks wrong: `as_kernel()` requests a download unconditionally,
ignoring the `Kernel._DOWNLOADS` global that `download()` exists to set. If the intent was
"this file may need fetching", the nearest honest expression is `exists=True`, which is the
parameter `KernelFile` actually has — though note §6.7, which has that parameter's logic
inverted.

---

### 6.20 A kernel that applies to every NAIF ID is never furnished — **critical** [confirmed]

> **Found and fixed 2026-08-16**, walking `Recipe.furnish()`. Not in the original draft:
> nothing had ever called `furnish()`, and this defect is invisible until you check *what*
> was furnished rather than whether the call raised.

`has_overlap()` ended with:

```python
        return bool(self.id_overlap(ids=ids))
```

An empty NAIF ID set means "applicable to every NAIF ID" -- `id_overlap()`'s own docstring
says so. But `id_overlap()` returns an empty set in two quite different situations: when
the two sets each name IDs and share none, and when neither side constrains the IDs at
all. Only the first is a failure to overlap. Observed:

```text
naif0012.tls   naif_ids=set()   id_overlap(None)=set()   has_overlap(None,None,None)=False
pck00011.tpc   naif_ids={...}   id_overlap(None)={...}   has_overlap(None,None,None)=True
```

Every LSK has an empty ID set, so with no ID constraint no LSK ever overlaps anything and
none is ever furnished:

```text
furnished LSK basenames: []
furnished PCK basenames: ['pck00011.tpc']
```

This is the most consequential defect found in the whole walk, and the least visible.
`Recipe.furnish()` returned cleanly; it had simply dropped the leapseconds kernel, on
which every SPICE time conversion depends. A test asserting only that `furnish()` does not
raise would still pass today.

**Fix**: return True when neither side constrains the IDs, before falling back to the
intersection test.

### 6.21 `time_overlap()` rejects the `dt=None` that `has_overlap()` passes it

> **Found and fixed 2026-08-16**, walking `Recipe.furnish()`.

`has_overlap()` is declared `(..., *, dt=None)` and documents that default as "use
Kernel.DT". It forwards `dt` unchanged, but `time_overlap()` only translated bools:

```python
        if isinstance(dt, (bool, np.bool_)):
            dt = Kernel.DT if dt else 0.
```

`None` fell through to `t1 < t0 - dt` and raised `TypeError: unsupported operand type(s)
for -: 'float' and 'NoneType'`. It stayed hidden until §6.17 was fixed *and* a real time
range was supplied, because before that both limits were `None` and the comparison was
skipped. Any call of the form `kernel.has_overlap(tmin, tmax)` hits it.

---

## 7. `KernelSet`, `KernelStack`, `Metakernel`, `Recipe`

`kernelstack.py` is unchanged; `recipe.py` changed by one moved import.

### 7.1 `KernelStack`'s requisite properties recurse infinitely — **critical**

> **Fixed 2026-08-16.** Each property now creates its set *before* the call that
> reads the property back, which breaks the cycle. The base class guards its lazy
> sets with `hasattr()`; this subclass pre-sets them to `None` in `__init__`, which
> defeats that guard, so `exclude()` and `require()` re-entered the property they
> were being called from.
>
> All four resolve now, and propagation works: an exclusion or co-requisite on a
> member kernel appears on the stack, and a member's prerequisite outside the stack
> (`naif0008.tls`) propagates up.
>
> **One observation to record honestly.** The stack's own members never appear in
> its prerequisites, because `_add_to_set()` deliberately drops any basename already
> in `self.basenames`. That makes the `for kernel in self._kernels[:-1]` loop -- the
> one whose comment says it preserves the load order -- a no-op. Order is in fact
> preserved by `is_ordered`, which `KernelStack` sets to True and which
> `_furnish_for()` honors directly. The loop is dead code rather than a defect, but
> it should either be removed or its comment corrected.

`src/spyceman/kernelstack.py:88-95`

```python
    @property
    def exclusions(self):
        if self._exclusions is None:
            for kernel in self._kernels:
                self.exclude(*kernel.exclusions)
        return self._exclusions
```

`self.exclude(...)` reaches `Kernel.exclude`, which calls
`self._add_to_set(self.exclusions, self.exclusions, kernels)` — re-entering this property
with `_exclusions` still `None`. The base class guards with `hasattr`; the subclass
initialises the attribute to `None` in `__init__` (lines 45–48), defeating that guard. All
four properties — `exclusions`, `prerequisites`, `postrequisites`, `corequisites` — share
the structure.

### 7.2 `KernelStack.prerequisites` unpacks a `Kernel` and forgets to unpack a set

> **Fixed 2026-08-16**, alongside §7.1, since both live in the same property and
> neither could be demonstrated without the other. `self.require(*kernel.
> prerequisites, above=False)` now unpacks the set, and `self.require(kernel,
> above=False)` passes the Kernel rather than trying to iterate it.

`kernelstack.py:114` passes `kernel.prerequisites` — a set — as a single kernel, where
lines 135 and 152 correctly unpack. Line 117 does `self.require(*kernel, above=False)`,
attempting to iterate a `Kernel`.

### 7.3 `KernelStack.used()` tests the wrong container

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. The test is now against `basenames`, the
> accumulator, matching `KernelStack.basenames` a few lines above.

`src/spyceman/kernelstack.py:233-237`

```python
            for basename in kernel_basenames:
                if basename in kernel_basenames:      # always True
                    basenames.remove(basename)
```

The condition should be `if basename in basenames`. As written it is vacuously true and
`basenames.remove()` raises `ValueError` on the first iteration. `KernelStack.basenames`
(lines 74–75) implements the same de-duplication correctly.

### 7.4 `KernelSet.__init__` reads two attributes that do not exist

> **Fixed 2026-08-16.** `KernelFile(basenames[0]).ktype` for the first, and
> `basename._basename` -- the loop variable rather than the class -- for the second.
> A KernelSet can now be built from basenames or from KernelFile objects, and the
> de-duplication works: `['naif0012', 'naif0011', 'naif0012']` yields
> `['naif0011', 'naif0012']`, keeping the last occurrence as documented.
>
> An empty list now raises `ValueError: a KernelSet must contain at least one kernel
> file`, as §7.15 recommended and as `Metakernel` already did, rather than
> `IndexError` from `basenames[0]`.
>
> That guard needed a caller that respects it. `Voyager._planet_spk()` built a
> KernelSet unconditionally, including when no flyby matched; it now returns None,
> which is what every other kernel function does when nothing satisfies the
> constraints. `_planet_spk(voyager=1, planet='URANUS')` and the Neptune case both
> return None; Jupiter and the Voyager 2 cases return a KernelSet.

`kernelset.py:37` — `KernelFile(basenames[0])._ktype`; `KernelFile` has no `_ktype`, only
the `ktype` property. `kernelset.py:45` — `basename = KernelFile._basename` references the
*class* rather than the loop variable.

### 7.5 `KernelSet` names itself `"None"`

> **Fixed 2026-08-16.** `self._name = str(name) if name else ''`, so a `None` name
> leaves the field empty and the lazy derivation in `Kernel.name` runs instead of being
> defeated by the truthy string `'None'`.


`kernelset.py:60` — `self._name = str(name)`. The documented default `name=None` means
"derive a name", but `str(None)` is the truthy string `'None'`, so `Kernel.name`'s
lazy-derivation guard never fires.

### 7.6 `Metakernel.basenames` returns `None` and collects the wrong type

> **Fixed 2026-08-16.** `basenames` walks the ktypes in dependency order, skips the
> absent ones, and returns the accumulated list of basename strings.


`metakernel.py:96-99` has no `return`. And by the time it runs, `_kdict`'s values are
`Kernel` objects rather than basename lists (lines 65–73), so even with a `return` it would
yield Kernels.

### 7.7 `Recipe._attribute_desc` reads `Recipe.RECIPES`

> **Fixed 2026-08-16.** Every site reads `Recipe._RECIPES`, which is the name the class
> actually defines.


`recipe.py:72` — the attribute is `_RECIPES`; the two sibling descriptors get it right
(lines 108, 148). This fires for every class-level attribute access, which is the entire
purpose of the descriptor.

### 7.8 `Recipe.furnish()` and `Recipe.used()` construct `KernelStack` wrongly — **critical**

> **Fixed 2026-08-16**, walking `Recipe.furnish()`. Both call sites now read
> `KernelStack(kernels, name=...)`. Before the fix the name string was taken as the
> kernel list and iterated character by character, giving
> `ValueError: invalid kernel file extension: 'd'`.

`recipe.py:736` and `:767` — `KernelStack(self._name + '_' + ktype, *kernels)`.
`KernelStack.__init__(self, kernels, *, name='')` takes the list first and `name` as
keyword-only. These are the two headline methods of the public API; `Recipe.furnish(tmin,
tmax)` is the call the README tells users to make before every calculation.

### 7.9 `_tkdict_desc.__get__` uses `self` where it means `obj`

> **Fixed 2026-08-16.** `__get__` substitutes the selected Recipe for `obj` when `obj is
> None`, and reads `obj` thereafter.


`recipe.py:149` — `getattr(self, ktype)` reads the descriptor, not the Recipe. Line 151
then calls `kernel.get_basenames()`, a method that exists nowhere in the package.

### 7.10 `_append_or_prepend` references attributes that do not exist, and recurses via the class

> **Fixed 2026-08-16.** `_append_or_prepend` is a normal method reached through `self`,
> and the attributes it touches exist. `__iadd__` calls it directly rather than routing
> back through the class.


`recipe.py:584` and `:590` use `self._local_meta` and `self._meta`; `__init__` creates
attributes named `'_' + ktype`, so the metakernel attribute is `_META`. Line 589 calls
`Recipe._append_or_prepend(subkernel, prepend=prepend)` — an unbound call that binds
`subkernel` to `self`.

### 7.11 `recipe += [...]` and the module's own bootstrap are broken

> **Fixed 2026-08-16.** `__iadd__` now calls `_append_or_prepend()` directly instead
> of routing through `_append(*kernels)`, which wrapped the whole operand in one more
> layer. `_append_or_prepend()` already normalizes a single kernel, a tuple, a set,
> or a list, so all four forms work. `__copy__` was fixed the same way, by unpacking:
> `dup._append(*self._kernels)`.
>
> One adjacent hazard was closed at the same time: `_append_or_prepend()` reversed
> its argument in place when prepending, so passing a list would have reversed the
> caller's own list. It now always builds a copy.
>
> **This was the last blocker. `import spyceman` now succeeds.**

`_append` is declared `_append(self, *kernels)`; `__iadd__` (line 621) passes the list as
one argument, so `_append_or_prepend` receives `([k1, k2],)`, converts it to `[[k1, k2]]`,
and then calls `.ktype` on a list. The documented syntax `recipe += [kernel, ...]` fails,
and so does the module's own last line:

```python
793    default += General.lsk(), General.pck()
```

which executes at import time. `Recipe.__copy__` (line 344) has the identical defect.

### 7.12 `__setstate__` and `_copy` have broken signatures

> **Fixed 2026-08-16.** `_copy` uses the `self=None` convention shared by the other
> wrapped methods, and `__setstate__` restores in place and returns nothing, as the
> pickle protocol requires.


`recipe.py:462` — `def __setstate__(state)` has no `self`, so unpickling binds the Recipe
to `state`; it also returns a new Recipe, which the protocol forbids. `recipe.py:347` —
`def _copy(self=None)` calls `__copy__` on `None` when the default is taken.

### 7.13 `_wrap_func` builds six public methods with `exec()` at import time

> **Fixed 2026-08-16.** The `exec()` construction is gone. `_wrap_func` now defines a
> real closure and calls `functools.update_wrapper()`, then sets `__signature__` from
> `inspect.signature(func)` so `help()` and static tools report the signature of the
> method being stood in for. The only remaining mention of `exec` in the file is the
> comment recording why it was removed.


`recipe.py:160-220`. The stated justification is making `help()` show the right signature,
which `functools.wraps` plus `__signature__` achieves without `exec`. The current form
depends on the interaction between `exec`'s implicit `locals()` snapshot and the enclosing
function scope, and it is invisible to static analysis — nothing can tell you
`Recipe.append` exists.

---

### 7.14 `Recipe.furnish()` and `Recipe.used()` cannot be called on the class

> **Found and fixed 2026-08-16**, walking `Recipe.furnish()`.

Every wrapped method documents five call forms, including `Recipe.furnish(...)` with no
Recipe at all, meaning "the currently selected Recipe". `_wrap_func()` copies the
underlying method's signature onto the generated wrapper, so whether that form works
depends entirely on whether the underlying method gives `self` a default:

```text
  _copy     (self=None)                            -> Recipe.copy()     works
  _rename   (self=None, name=None)                 -> Recipe.rename()   works
  _furnish  (self, tmin=None, tmax=None, ids=None) -> Recipe.furnish()  TypeError
  _used     (self, tmin=None, tmax=None, ids=None) -> Recipe.used()     TypeError
```

`_copy` and `_rename` declare `self=None`; `_furnish` and `_used` do not. **Fix**: declare
`self=None` on both, matching the two that already work. `_append` and `_prepend` share
the omission but are reached only with at least one argument, so the documented forms
happen to work.

### 7.15 `Recipe.furnish()` builds a `KernelStack` for ktypes it has no kernels for

> **Found and fixed 2026-08-16**, walking `Recipe.furnish()`.

Both `_furnish()` and `_used()` loop over all ten entries of `_KTYPES` and construct a
`KernelStack` for each. A Recipe normally carries kernels for only a few, so the rest
produce `KernelStack([])`, and its constructor indexes `self._kernels[0]` to determine the
ktype: `IndexError: list index out of range`. The `default` Recipe has kernels for two of
the ten, so eight of the ten iterations raised.

**Fix**: skip a ktype with no kernels. `KernelStack` would also be improved by rejecting an
empty list with a clear message, as `Metakernel` already does.

---

## 8. `_spicefunc`

> **Added 2026-08-16, after the fact.** This section was missing from the first draft of
> this review: `_spicefunc.py` was covered only obliquely, through the naming-drift table
> in §11.3. That was an oversight, and it mattered — §8.3 is where `import spyceman` stops
> once §4.2 and §6.6 are repaired, and nothing in the document said so.

`_spicefunc()` builds the public `spk()`, `pck()`, and `ck()` functions that every
`hosts/` and `solarsystem/` module exposes, and it runs at import time for each of them.
Apart from the rename and the debug print removed in §1.4, the file is unchanged from the
previous revision.

### 8.1 `LOCAL` is tested, `LOCALS` is assigned — **critical**

> **Fixed 2026-08-16.** The three `LOCALS` sites became `LOCAL`, which is the canonical
> name: it is the one initialized at line 417 and it pairs with `LOCAL_AND_REMOTE`.
> `General.lsk.LOCAL` now holds its six sorted basenames instead of staying empty, and
> the `if not func.LOCAL` guard caches rather than re-scanning on every call.

`src/spyceman/_spicefunc.py:177-199`

```python
177    if not func.LOCAL:
...
184        func.LOCALS = list(basenames)
185        func.LOCALS.sort(key=func.SORT)
...
199        basenames = func.LOCAL
```

`LOCAL` is initialized to `[]` at line 413 and never written again, so the guard at line
177 is always true — the scan re-runs on every call — and `basenames` at line 199 is always
the empty list. `LOCALS`, the attribute actually written, is read only at line 190.

The non-`renew` path is the default path, so every generated kernel function currently
selects from zero candidates, and `filter_basenames` then raises `IndexError` on
`basenames[0]` (§6.14).

### 8.2 `DEFAULT_TIMES_KEY` and `DEFAULT_IDS_KEY` are never assigned

> **Fixed 2026-08-16.** The readers were renamed to `DEFAULT_TIME_KEY` and
> `DEFAULT_ID_KEY`, matching the attributes actually assigned and, in turn, the
> `default_time_key` / `default_id_key` parameters they come from. The plural forms
> were the odd ones out. `func_template()` now clears both default-filling blocks and
> reaches §8.10.

Read at lines 154 and 168; the attributes assigned at lines 423 and 425 are
`DEFAULT_TIME_KEY` and `DEFAULT_ID_KEY`, singular. `AttributeError` on every call to every
generated kernel function that defines a default-times or default-IDs key.

### 8.3 `wrapper.NOTES` is read but never assigned — **blocking** [confirmed]

> **Fixed 2026-08-16.** `NOTES=notes` now uses the parameter that was already being
> accepted and discarded; no `wrapper.NOTES` attribute was added, since nothing reads
> one. `{NOTES}` in the template gained the trailing backslash that `{PROPERTIES}`
> already used, so an empty notes block contributes nothing rather than a stray blank
> line, and `notes` is normalized to end with exactly one blank line when non-empty.
> Verified against the real template and the real `_ck_notes`: both the empty and the
> populated case render with no doubled blank lines and no line over 90 columns.
>
> This unblocked every `_spicefunc()` call in the package. `import spyceman` now
> builds all the generated kernel functions, reaches `recipe.py:793`, and fails
> *calling* one of them — at §8.2.

`src/spyceman/_spicefunc.py:403-405`

```python
    wrapper.__doc__ = DOCSTRING_TEMPLATE.format(TITLE=title,
                                                PROPERTIES=property_docs,
                                                NOTES=wrapper.NOTES)
```

Nothing ever sets `wrapper.NOTES`; a search of the file finds no `wrapper.NOTES =`. The
`notes` parameter is accepted at line 348 and never used. This raises inside
`_spicefunc()` itself, so every module that calls it fails to import.

With §4.2 and §6.6 repaired, this is where `import spyceman` now stops:

```text
  File "src/spyceman/solarsystem/General.py", line 32, in <module>
    lsk = _spicefunc('lsk',
  File "src/spyceman/_spicefunc.py", line 405, in _spicefunc
    NOTES=wrapper.NOTES)
AttributeError: 'function' object has no attribute 'NOTES'
```

The fix is presumably `NOTES=notes`, with `notes` defaulting to `''`; note that
`DOCSTRING_TEMPLATE` expects the value to end with its own blank line.

### 8.4 `tmax` defaults to the minimum of the candidate maxima

> **Fixed 2026-08-16.** `tmax` defaults to `max(...)` over the candidate maxima,
> matching `tmin`'s use of `min(...)`.


`src/spyceman/_spicefunc.py:156-159` — the `tmin` branch takes `min(...)` and the `tmax`
branch takes `min(...)` as well. The second should be `max`. Combining several default
time ranges yields the narrowest upper bound rather than the widest.

### 8.5 `KernelFile.search_fancy_index` does not exist

> **Fixed 2026-08-16.** `search_fancy_index` is imported from `_downloads`, where it is
> defined, instead of being reached for as a `KernelFile` attribute.


`_spicefunc.py:193`. The function lives in `_downloads`, not on `KernelFile`. This is the
`renew=True` path.

### 8.6 `sorted` shadows the builtin and its result is discarded

> **Fixed 2026-08-16.** The shadowing local is gone. The sort key is built once and
> applied in `func_template()`, where the known and discovered basenames are combined; a
> comment records why the known basenames are deliberately not ordered here.


`src/spyceman/_spicefunc.py:372-373`

```python
    sorted = list(known)
    sorted.sort(key=sort)
```

`sorted` is never read afterwards, so the sort is thrown away and `known` remains the
unordered `set` built on the previous line. The `ordered=True` option therefore cannot
preserve the order of the `known` list the caller supplied. Two defects and a shadowed
builtin in two lines.

### 8.7 `result.exclude()` is passed a set instead of unpacked kernels

> **Fixed 2026-08-16.** Now `result.exclude(*unused_basenames)`. Verified by
> intercepting `_add_to_set`: it receives `("naif0010.tls", "naif0011.tls")`, two
> basename strings, where it previously received a one-element tuple holding the
> whole set. See §8.11 for what this uncovered.
>
> With §8.11 fully closed, this line does its job: `General.lsk()` returns
> `KernelFile("naif0012.tls")` -- the newest LSK -- carrying the five older ones as
> exclusions, and `General.pck()` returns `pck00011.tpc` with seven older PCKs
> excluded. None of those excluded files exists locally, which is exactly the case
> that used to raise.

`_spicefunc.py:255` — `result.exclude(unused_basenames)`. `exclude(*kernels)` treats the
set as a single kernel; `isinstance(kernel, str)` is false, so it falls through to
`kernel.ktype`. Should be `result.exclude(*unused_basenames)`.

### 8.8 The exclusion pass is a no-op

> **Fixed 2026-08-16.** The pass computes `unused_basenames` as a set difference and
> calls `result.exclude(*unused_basenames)`, so the names are unpacked as the signature
> expects rather than passed as a single set.


`src/spyceman/_spicefunc.py:229-232`

```python
            keys = exclusion_keys(property_values, kfile)
            if not (keys in keys_found):
                keys_found |= keys
```

`exclusion_keys()` returns a `set` of tuples. `keys in keys_found` asks whether that set
*object* is an element of `keys_found`, while `keys_found |= keys` adds its *elements*. The
membership test can never succeed, so no kernel is ever skipped.

### 8.9 The wrapper's signature does not match its generated documentation

> **Fixed 2026-08-16.** The wrapper signature is now `(version=None, *, tmin, tmax, ids,
> basename, release_date, expand, renew, **properties)`, which is exactly what
> `DOCSTRING_TEMPLATE` documents and what `func_template()` accepts. The previous
> signature took `dates`, `download` and `verbose`, none of which `func_template()` has
> a parameter for, while omitting `basename`, `release_date` and `renew` -- so those
> three silently fell into `**properties` and were treated as property constraints.
> Verified against `General.lsk(release_date='2010-01-01')`, the form the README uses,
> which now selects `naif0009.tls` rather than ignoring the constraint.


`wrapper` (line 332) accepts `version, tmin, tmax, ids, dates, expand, download, verbose,
**properties` and forwards `tmin, tmax, ids, dates, version, expand, **properties`
(line 361).

- `func_template` has no `dates` parameter, so `dates` lands silently in `**properties`
  and is applied as a property filter.
- `basename`, `release_date`, and `renew` *are* parameters of `func_template` and *are*
  documented in `DOCSTRING_TEMPLATE`, but `wrapper` neither accepts nor forwards them. A
  user following the generated help and calling `spk(release_date='2018-01-01')` — the
  exact example in the project README — gets it absorbed into `**properties` and silently
  treated as a constraint on a property of that name.
- `download` and `verbose` are accepted and dropped.

---

### 8.10 `func.REDUCE` is read but never assigned — **blocking** [confirmed]

> **Fixed 2026-08-16.** `wrapper.REDUCE = reduce` added between `EXCLUDE` and `ORDERED`,
> matching the order of the parameters in the signature. Verified per function:
> `General.spk.REDUCE` is `True`, which is how it is declared, while `lsk` and `pck` are
> `False`. Re-running the assigned-vs-read audit now reports no attribute read without
> being assigned; `FUNCNAME` remains assigned and never read, which is harmless.
>
> **Found 2026-08-16**, while verifying the §8.2 fix. Not in the original draft: nothing
> had ever executed far enough into `func_template()` to reach line 208.

`src/spyceman/_spicefunc.py:206-208`

```python
    kfiles = KernelFile.filter_basenames(kfiles, tmin=tmin, tmax=tmax, ids=ids,
                                         ...
                                         reduce=func.REDUCE)
```

`_spicefunc()` accepts a `reduce` parameter (line 269) and documents it (line 300), but
never attaches it to `wrapper`. Auditing the two sides against each other:

```text
assigned: DEFAULT_ID_KEY DEFAULT_IDS DEFAULT_PROPERTIES DEFAULT_TIME_KEY DEFAULT_TIMES
          EXCLUDE FUNCNAME KNOWN LOCAL LOCAL_AND_REMOTE ORDERED PROPNAMES REQUIRE
          SHADOWS SORT SOURCE UNKNOWN
read:     DEFAULT_ID_KEY DEFAULT_IDS DEFAULT_PROPERTIES DEFAULT_TIME_KEY DEFAULT_TIMES
          EXCLUDE KNOWN LOCAL LOCAL_AND_REMOTE LOCALS ORDERED PROPNAMES REDUCE REQUIRE
          SHADOWS SORT SOURCE UNKNOWN
```

`REDUCE` is read and never assigned; `FUNCNAME` is assigned and never read; `LOCALS` is
the §8.1 pair. This is the same defect as §8.3 — a parameter accepted, documented, and
then dropped on the floor — and the fix is the same shape: `wrapper.REDUCE = reduce`
alongside the other attributes.

The audit itself is worth keeping. Comparing the set of `wrapper.X` assignments against
the set of `func.X` reads is a two-line check that would have caught §8.1, §8.2, §8.3, and
this one in a single pass, and it needs no linter.

---

### 8.11 Excluding a kernel tries to download it — **critical** [confirmed]

> **Found 2026-08-16**, immediately after the §8.7 fix. This is an interaction between
> three separate defects rather than a new one of its own, which is why none of them
> individually predicted it. It is recorded here because it changes the order the
> remaining fixes should be applied in.

With §8.7 fixed, `func_template()` reaches `_add_to_set()` with a basename string, and
that method does:

```python
                if is_basename(kernel):
                    basenames = {kernel}
                    kfile = Kernel.KernelFile(kernel, exists=True)
```

`exists=True` on a file with no local copy should raise. Because §6.7 has that test
inverted, it instead calls `must_exist()`, which reads `self.dest` and trips §4.5:

```text
naif0010.tls present locally?  False
Kernel._DOWNLOADS = True
```

So the chain currently terminates in an `AttributeError` from §4.5. **Fixing §4.5 on its
own would replace that with a network download attempt during `import spyceman`** — for
the very files the caller is trying to *exclude*.

Three things are wrong here and they want fixing together:

1. §4.5, the `_rules_values` misspelling, is the immediate symptom.
2. §6.7, the inverted `exists` test, is what routes a missing file into `must_exist()`.
3. More fundamentally, `_add_to_set()` has no business requiring that an excluded kernel
   exist at all. An exclusion is a statement about what must *not* be furnished; it needs
   the basename's ktype, which comes from the extension, and nothing more. The
   `exists=True` argument looks like it was meant to assert "this is a real kernel", but
   the class has `is_known` for that and it does not touch the filesystem.

Until at least (2) is resolved, do not fix §4.5 in isolation, or an ordinary import will
start reaching for the network.

> **Resolved 2026-08-16.** All three fixed, in order. (3) was closed by having the
> basename branch of `_add_to_set()` take its ktype from `basename_ktype()`, the
> pure-string helper the regular-expression branch beside it already used, rather
> than constructing a `KernelFile` with `exists=True` purely to read `.ktype` off it.
> The filesystem is no longer touched on this path at all.
>
> With all three closed, `General.lsk()` and `General.pck()` return real objects for
> the first time -- see the note on §8.7.

---

## 9. Local files and downloads

### 9.1 `_get_spicepath()` has its arguments reversed — **critical** [confirmed]

> **Fixed 2026-08-16.** Now `os.environ['SPICEPATH'].split(':')`. Empty entries are
> dropped as well: a leading, trailing, or doubled colon would otherwise yield an
> empty string, which becomes `Path('')` and resolves to the working directory --
> so a stray colon would have set the library walking the user's whole current
> directory tree.
>
> Verified with `SPICEPATH` set to two roots and a trailing colon: both roots are
> returned, the empty entry is not, and `KernelFile.walk()` with no arguments
> discovers the kernels nested beneath each one and registers them with correct
> absolute paths. `KernelFile('naif0012.tls').exists` is then True.
>
> This is the first time the library has been able to find a user's own kernels,
> which is the setup step the README opens with.

`src/spyceman/_localfiles.py:60`

```python
        return ':'.split(os.environ['SPICEPATH'])
```

```text
as written  -> [':']
as intended -> ['/spice/kernels', '/more/kernels']
```

`SPICEPATH` is the one required environment variable and this is the only function that
consumes it, so kernel discovery cannot work. See also §1.6.

### 9.2 `use_path()` concatenates a `str` and a `Path`

> **Fixed 2026-08-16.** Rebuilt as an f-string. The duplicate-basename
> warning now issues instead of raising `TypeError`, which matters because that is
> exactly the case it exists to report.

`_localfiles.py:127-129` builds its warning with `'    ' + path + '\n'`, where `path` is a
`pathlib.Path` (line 88). This is the warning that fires when a user has two different
kernels with the same basename — the exact case it exists to report.

### 9.3 `use_path()` uses `set.remove` where `discard` is needed

> **Fixed 2026-08-16.** `discard`, so removing a basename that was
> never registered under META is a no-op rather than a `KeyError`.

`_localfiles.py:141` — `BASENAMES_BY_KTYPE['META'].remove(basename)` raises `KeyError` if
absent. The preceding line checks membership in `KERNELINFO`; nothing protects this one.

### 9.4 `.tm` files are never checked for being metakernels

> **Fixed 2026-08-16.** The test is now `_EXTENSIONS[ext] == 'META'`,
> so it covers both extensions that claim to be metakernels rather than only `.txt`.
> A `.tm` without a KERNELS_TO_LOAD assignment is rejected; a real one is accepted and
> registers with ktype META.

`_localfiles.py:134` applies `_is_metakernel()` only to `.txt`. But `_ktypes.py` maps both
`.txt` and `.tm` to `META`, and `.tm` is the *conventional* metakernel extension — the
comment beside `.txt` says that one is the doubtful case. The check is applied to the
wrong extension, or at least not to both.

### 9.5 `retrieve_online_file()` builds label URLs from the full URL

> **Fixed 2026-08-16.** The stem is taken from `basename`. The label
> requests are now `.../naif0012.tls.lbl`, `.../naif0012.lbl` and `.../naif0012.cmt`,
> where before the last two were built from the whole URL and came out as
> `http://host/dir/http://host/dir/naif0012.lbl`.

`_downloads.py:157-158` — `stem` is taken from the stem of `url`, which is the full
`source + '/' + basename`. Those names are passed back in as `basename` to the recursive
call, which prefixes them with `source` again, producing `https://.../https://...lbl`. It
should be the stem of `basename`.

### 9.6 `retrieve_online_file()` double-prefixes the destination on recursion

> **Fixed 2026-08-16.** The resolved directory is held in a separate
> `destdir`, leaving `dest` unchanged for the recursive calls. All four files land in
> `General/LSK/` rather than the labels going to `General/LSK/General/LSK/`.

`_downloads.py:144` rebinds `dest = _DOWNLOADS / dest`, and lines 161 and 164 pass that
already-prefixed value into the recursive call. When `_DOWNLOADS` is absolute this is
masked, but the fallback at line 18 is the relative `Path('spice-downloads')`, for which
labels land in `spice-downloads/spice-downloads/...`.

### 9.7 `get_fancy_index_table()` has a dead line and an unguarded match

> **Fixed 2026-08-16.** The dead `row.split('<')` is gone, and a row
> that does not parse is skipped rather than dereferencing `None`. A page carrying
> header, separator, and malformed rows now yields just its file rows, where one bad
> row previously abandoned the whole index.

`_downloads.py:78-83` — line 78's `parts = row.split('<')` is overwritten on the next line,
and line 83 dereferences `_FIELDS.match(row)` without a `None` check, so any row that does
not fit the pattern aborts the whole index parse.

### 9.8 `search_fancy_index()` returns two different types

> **Fixed 2026-08-16.** Always a set; an exact filename yields a
> one-element set. This also repairs its caller in `_spicefunc.py`, which does
> `set(...)` on the result -- against the old bare string that produced a set of
> single characters.

`_downloads.py:192-198` returns a bare `str` when the pattern names a file exactly and a
`set` otherwise. Callers cannot use the result without type-testing it.

### 9.9 `latin8` is the Celtic alphabet, almost certainly meant to be `latin-1`

> **Fixed 2026-08-16.** All four text opens use `latin-1`, and the
> binary DAF sniff reads bytes -- `open(path, 'rb')`, splitting on `b'/'` -- rather
> than decoding a binary file as text. No `latin8` remains in the package.

`_downloads.py:52` and `_kernelinfo.py:335, 361, 368, 412`. Python resolves `latin8` to
ISO-8859-14, which replaces a dozen positions in the 0xA0–0xFF range with Welsh and Irish
letters. For ASCII kernels the practical effect is nil, but it is not what was meant.
`_kernelinfo.py:368` additionally opens a *binary* DAF file in text mode with this encoding
to sniff its first 20 bytes; that should be `open(path, 'rb')`.

### 9.10 `_cspyce.py`: `numbers` is used but never imported

> **Fixed 2026-08-16.** `import numbers` added. The spicepy fallback
> path can now run at all, though it remains unexercised; see the closing note on
> whether that path is meant to be supported.

`_cspyce.py:114` — `isinstance(i, numbers.Integral)` inside `_fake_define_body_aliases`,
in a module that imports only `importlib` and `os`. This is on the `spicepy` path, which is
strong evidence that path has never executed. The module also monkey-patches the imported
`cspyce` module in place (lines 129–141), mutating global state for every other consumer of
`cspyce` in the process.

---

## 10. Host and solar-system modules

### 10.1 `_input_set()` is called with a keyword it does not accept — two different spellings

> **Fixed 2026-08-16.** `_input_set()` gained the `ranges` parameter
> both callers were reaching for, and `spk.py` now spells it the same way `ck.py` does.
> A two-element **list** of integers expands to the inclusive range it spans, matching
> the convention `_test_version()` already uses for versions; a tuple or set of two is
> left alone, because only a list carries order.

`src/spyceman/_utils.py` declares `_input_set(value, default=set())`. Callers:

- `hosts/Cassini/spk.py:256` — `_input_set(version, range=True)`
- `hosts/Cassini/ck.py:218` — `_input_set(version, default={1, 2, 3}, ranges=True)`

Neither `range` nor `ranges` exists. Both raise `TypeError`. That the two sites disagree on
the spelling suggests a parameter that was planned and never implemented; if version ranges
are meant to be expandable here, `_input_set` needs that feature.

### 10.2 `jupiter_ck_adapted()` subscripts the set instead of the element

> **Fixed 2026-08-16.** The comprehension tests `b[6:7]` rather than
> `basename[6]`, which also means a basename shorter than seven characters no longer
> raises `IndexError`. `_jupiter_ck_adapted()` now returns a KernelFile.

`src/spyceman/hosts/Cassini/ck.py:228`

```python
    basename = {b for b in basename if basename[6] == '_'}
```

`basename` is the set built on the previous line; `b` is the loop variable that was meant.
`set` is not subscriptable, so this raises `TypeError` for any non-empty input.

### 10.3 `planet_spk()` deletes from a set — [confirmed]

> **Fixed 2026-08-16.** Two `flybys.discard(...)` calls. The set is
> now built correctly: Voyager 1 yields Jupiter and Saturn only, Voyager 2 yields all
> four planets, and asking for Voyager 1 at Uranus yields an empty set and a `None`
> return rather than a `TypeError`.

`src/spyceman/hosts/Voyager/__init__.py:534-535`

```python
    del flybys[1, 'URANUS']
    del flybys[1, 'NEPTUNE']
```

`flybys` is a `set` built on the preceding lines.

```text
TypeError: 'set' object does not support item deletion
```

The intent — removing the two flybys that never happened — needs `flybys.discard((1,
'URANUS'))`.

### 10.4 `General.py` compares toolkit versions as strings

> **Fixed 2026-08-16.** The release number is extracted and compared
> numerically.
>
> **Correction to the claim below:** it said the comparison is "wrong at `N0100`". It is
> not. NAIF zero-pads to four digits, and string comparison orders those correctly --
> `'CSPICE_N0100' <= 'CSPICE_N0066'` is `False`, which is right. It breaks only if the
> digit count ever changes: `'CSPICE_N00100' <= 'CSPICE_N0066'` is `True`, which is
> wrong. So this was a latent fragility rather than a live defect, and the fix removes
> the dependence on a formatting convention NAIF has not promised to keep.

`solarsystem/General.py:66` — `CSPYCE.tkvrsn('toolkit') <= 'CSPICE_N0066'`. Correct for the
current fixed-width format, wrong at `N0100`.

### 10.5 The underscore-prefix convention is applied unevenly

> **Withdrawn 2026-08-16.** This finding is stale. Every helper it named is already
> private: `_spk_sort_key` in `General.py`, `_pck_sort_order` in `Saturn.py`,
> `_jupiter_ck_sort_key` and `_ck_sort_key` in `Cassini/ck.py`, `_tour_spk_sort_key` in
> `Cassini/spk.py`. The un-prefixed names that remain -- `lsk`, `pck`, `spk`, `ck`, `fk`,
> `ik`, `sclk`, `meta`, and the body and frame tables -- are the modules' public API and
> are documented as such. `Voyager/__init__.py` does leave a loop variable named `keys`
> at module scope, but it is deleted a few lines later.
>
> What genuinely varies is whether a module declares `__all__`: `General.py`,
> `Cassini/spk.py`, and `Cassini/__init__.py` do; `Saturn.py`, `Cassini/ck.py`, and
> `Voyager/__init__.py` do not. That is worth settling, but it is a smaller and
> different point than this finding made.

This revision replaced the old "`del` the temporaries at the end of the module" idiom with
an underscore-prefix convention. It is not applied consistently: `General.py` now uses
`_lsk_source`, `_rule`, and `_pck_source`, but leaves `spk_sort_key`, `lsk`, `pck`, and
`spk` un-prefixed, and `Cassini/ck.py` leaves `jupiter_ck_sort_key` and `ck_sort_key`
public while prefixing `_rule` and `_gapfill_ck_notes`. Since the two idioms now coexist
across the package, `CLAUDE.md`'s description of the `del` idiom is out of date.

---

### 10.6 Five defects that only surfaced when the host packages were first imported

> **Found and fixed 2026-08-16.** Nothing had ever imported `spyceman.hosts.Cassini` or
> `spyceman.hosts.Voyager` -- `import spyceman` does not reach them -- so these had never
> executed. They are grouped here because they share a cause: each is a name that was
> changed on one side of a boundary and not the other.

1. **Fifteen `_spicefunc()` calls passed `default_times_key` and `default_ids_key`**,
   which the signature spelled `default_time_key` and `default_id_key`. **This reverses
   the direction taken for §8.2.** There, with only the internals visible, the singular
   forms looked authoritative and the readers were renamed to match. Seeing the callers
   changes the balance decisively: fifteen call sites across seven modules use the plural,
   they pair naturally with the `default_times` and `default_ids` dictionaries they key
   into, and the original docstring used them too. The signature, the attributes, and the
   readers all moved to the plural instead.

2. **`Saturn.py` called `KernelFile.supersede()`, which was never implemented.** The
   method with those semantics is `shadow()`: both kernels stay furnished and the first
   takes precedence wherever they overlap, which is what a Saturn rotation-model PCK does
   to the general NAIF PCK.

3. **`_CRUISE_SPKS.py` defined `_CRUISE_SPK_KTUPLES`.** Every one of the other 33
   generated tables names its list after its file; this one did not, and four sites in
   `Cassini/spk.py` imported the name the convention implies.

4. **`Cassini/__init__.py` still imported `BODY_ID`** from `_utils.py`, where §1.2 had
   renamed the definition to `_BODY_ID`. F821 cannot see this: a failed *import* is not an
   undefined *name*. Since the package documents `BODY_ID` in its docstring and lists it in
   `__all__`, the import now re-exports it under the public name.

5. **The FK and IK source lists assumed `_source()` returns one URL.** It returns two, so
   `_fk_source + f'/release.{i:02d}'` was a tuple plus a string. The release subdirectories
   are now built for each archive.

Plus one in Voyager: **six lookups read `_FRAME_IDS_BY_VOYAGER[vgr, instrument]`**, but
that dictionary is keyed by the spacecraft number alone. The tuple-keyed dictionary is
`_DEFAULT_FRAME_IDS`, which was built and never read.

The general lesson is the one §11.1 draws: an incomplete rename is this codebase's
characteristic defect, and neither the linter nor a passing import will find it. Only
executing the module does.

### 10.7 `ktupler.py` emitted a date julian cannot read back — **[confirmed]**

> **Found and fixed 2026-08-16**, while first importing `hosts/Cassini`, which pulls in
> `solarsystem/Saturn.py`.

`programs/ktupler.py` decides whether to emit a time as a quoted date or a raw TDB float:

```python
    if date[4] != '-':      # if not a four-digit year
        time = str(tdb)
```

The test is meant to detect a year that is not four digits. But `-501-12-05` also carries
`-` at index 4, so a negative year passed the test and was emitted as a quoted string --
and `julian` cannot parse a negative year in ISO form under any option, though it will
happily *produce* one via `format_day()`.

One such value reached the data: `sat441xl_part-1.bsp` in `_SATURN_SPKS.py` began at
`'-501-12-05T23:59:17.816'`. The date is genuine; SAT441 spans 501 BCE to 4500 CE. Loading
Saturn's SPK table raised `JulianParseException` on it.

**Fixed in both places.** The guard is now `date[4] == '-' and date[:4].isdigit()`, which
also rejects a five-digit year, and the one datum was replaced with the TDB value
`-78895166399.99977`, reconstructed by inverting ktupler's own conversion and checked to
round-trip back to the original string.

Note that `programs/` sits outside the packaged tree and outside every check CI runs, so
the generator that produces 13,600 lines of data is neither linted nor tested. That was
noted in §1.7 and this is the first concrete consequence.

---

## 11. Cross-cutting patterns

### 11.1 Incomplete renames are now the dominant failure mode

> **Recorded 2026-08-17.** This section is an analysis of the pattern rather than a
> separate defect, and the individual instances it cites are fixed under their own
> numbers. It is kept as the rationale for two of the changes made this revision: the
> `register()`/`lookup()` pair in §11.2, and the docstring conformance test in §12.5,
> which fails on a parameter documented under a name the signature does not have -- the
> static half of exactly this failure mode.


Three of this revision's four fatal defects are the same mistake: a definition was renamed
and its references were not.

| Renamed | References left behind | Location | Caught by the configured lint? |
|---|---|---|---|
| `BODY_ID` → `_BODY_ID` | 10 | `Cassini/_utils.py:41-54` | **yes** |
| (import removed) | 104 | `_AS_FLOWN_CKS.py` | no — file is excluded |
| `spicefunc.py` → `_spicefunc.py` | 1 | `__init__.py:14` | no — not a lint error |

The first is caught by the project's own `ruff` configuration, which means
`./scripts/run-all-checks.sh` fails today on this revision — I ran it, and `Code - Ruff
check` is the one failing check. That is worth pausing on: the repository's gate already
detects one of these defects and the revision was committed anyway.

The second is invisible to the configured run because `pyproject.toml` excludes the
generated `_UPPERCASE.py` tables from linting. That exclusion is reasonable for
machine-generated data, but it means a hand-edit to one of those files — which is what
happened here — gets no checking at all.

The third is not a Pyflakes-detectable error in any configuration: importing a module that
does not exist is a runtime failure, not a static one. Only an import test catches it,
which is why §12.5 and Step 2 below matter more than more linting would.

### 11.2 Two registries that are supposed to agree, and do not

> **Fixed 2026-08-16.** `_KernelInfo.register(basename, abspath)` is the single entry
> point that writes all three registries, and `lookup()` is the only read path.
> `_localfiles.use_path()` calls it, so a file discovered by walking the filesystem is
> now present in `KERNELINFO` as well as `ABSPATHS`. This is what closed §4.8.


`_KernelInfo` maintains three parallel class-level dictionaries — `ABSPATHS`,
`KERNELINFO`, `BASENAMES_BY_KTYPE` — with no invariant tying them together and no single
function responsible for consistency. `_localfiles.use_path()` writes `ABSPATHS` and
`BASENAMES_BY_KTYPE` but not `KERNELINFO` (lines 150–151); `_KernelInfo.__init__` writes
`KERNELINFO` and `BASENAMES_BY_KTYPE` but not `ABSPATHS` (lines 91–92); `replace()` writes
`KERNELINFO` and `ABSPATHS` (lines 1181–1192). §4.8 is the first place this bites.

A single `register(basename, abspath)` maintaining all three, with `lookup()` as the only
read path, would make the class of bug impossible.

### 11.3 Singular/plural and prefix drift in attribute names

> **Recorded 2026-08-17.** Like §11.1, an analysis rather than a separate defect; each
> instance is fixed under its own number (§4.1, §4.5, §6.6, §8.1, §8.2, §8.3, §8.10).
> Two of the drifting names were resolved by moving the signature rather than the
> readers -- `DEFAULT_TIMES_KEY` and `DEFAULT_IDS_KEY` became plural because fifteen
> call sites already read them that way.


Six independent defects share one shape — an attribute written under one name and read
under another differing by a suffix, prefix, or plural:

| Written | Read | Location |
|---|---|---|
| `LOCALS` | `LOCAL` | `_spicefunc.py:184` / `:177` |
| `DEFAULT_TIME_KEY` | `DEFAULT_TIMES_KEY` | `_spicefunc.py:424` / `:154` |
| `DEFAULT_ID_KEY` | `DEFAULT_IDS_KEY` | `_spicefunc.py:426` / `:168` |
| `_naif_ids_as_found` | `_naif_as_found` | `_kernelinfo.py:71` / `:466, 472` |
| `_rule_values` | `_rules_values` | `_kernelinfo.py:130` / `:1006, 1033` |
| `_date_group` | `date_group` | `rule.py:382` / `:470` |

The module-level cases are caught by `ruff`; the instance-attribute cases need a type
checker or a test.

### 11.4 Bare `except` and silent fallbacks hide the defects

> **Fixed 2026-08-17.** The three sites are addressed differently, because they were
> swallowing different things.
>
> `rule.py` was fixed under §5.10.
>
> `_kernelinfo.py` (comment extraction from a binary kernel) still falls back to an
> empty list, because comments are genuinely optional and a kernel without readable ones
> is not an error -- but it now issues a warning naming the file and the exception,
> since a corrupt kernel usually surfaces here first.
>
> `_utils._test_version()` was conflating two unrelated `TypeError`s: a `None` range
> limit, meaning that end is unconstrained, and a version that genuinely cannot be
> compared to the limit. The `None` case is now an explicit test, so only real
> incomparability reaches the `except`. That case still counts as a non-match rather
> than an error, which is deliberate: versions can be integers, tuples or strings, and
> one file whose version cannot be compared to the constraint must not abort a filter
> running over every other file. The behavior is pinned by `tests/test_utils.py`,
> including the case where one of a file's versions is incomparable and another is in
> range.


`rule.py:548` (`except Exception: pass`), `_kernelinfo.py:385` (`except Exception:` setting
`self._comments = []`), and the `try`/`else` ladder in `_utils._test_version` all convert
errors into silently wrong results. §5.10's stale-capture bug is invisible precisely
because of `rule.py:548`. Given how many `AttributeError`s this package currently raises,
these handlers work against the debugging effort and should be narrowed before any bring-up
work starts.

---

## 12. Repository and tooling

### 12.1 The linter is configured not to see the bugs

> **Superseded 2026-08-16, resolved 2026-08-17.** Ruff was first disabled outright, with
> the stale `per-file-ignores` deleted rather than left inert. It is now switched back on
> at `select = ["F"]` in all three places it runs. The prediction below held on the first
> run: F found an undefined name, and it was one this review had introduced. See item 2
> of "What to do next" for the detail and for why the wider rule set was measured and
> declined. `ruff format` remains off, since the house style is column-aligned.

`pyproject.toml` selects only `F`, excludes `src/spyceman/_downloads.py` entirely, and
carries `per-file-ignores` suppressing `F821`/`F841`/`F401` in `_cspyce.py`,
`_kernelinfo.py`, `_localfiles.py`, and `_utils.py`. Those entries were added as markers
for specific defects, three of which are now fixed. Two are not: `_cspyce.py`'s undefined
`numbers` (§9.10) and `_kernelinfo.py`'s `_rules_values` (§4.5, which `F821` does not catch
in any case, being an attribute rather than a name).

Every suppression that no longer corresponds to a live defect should be deleted, and the
remaining ones re-verified. The gap is measurable: `ruff check src --select F --isolated`
reports 115 errors today, while the configured run reports 10 — all of them §1.2. The
missing 105 are the 104 in `_AS_FLOWN_CKS.py` and the one in `_cspyce.py`.

The `F401` per-file-ignore on `src/spyceman/__init__.py` deserves separate thought. It
exists because that module's imports are re-exports, which is legitimate — but it is also
the reason nothing flagged line 14 as importing a name from a module that no longer exists.
Declaring the re-exports in `__all__`, rather than suppressing the rule, would keep the
check alive.

### 12.2 `git` still has `hosts/cassini` in lower case

> **Fixed 2026-08-17.** Renamed in the index with a two-step `git mv` through a
> temporary name, which is what a case-insensitive filesystem requires; git records it
> as a pure rename, so the history of all eighteen files is preserved. `git ls-files`
> now reports `src/spyceman/hosts/Cassini`, matching the directory on disk, the
> `spyceman.hosts.Cassini` in the README, the package's own docstring, and its sibling
> `Voyager`. `tests/test_hosts_slow.py::test_host_package_is_capitalized` fails on a
> case-sensitive filesystem if this ever regresses.


The working tree has `Cassini`; the index has `cassini`. macOS's case-insensitive
filesystem hides this locally. A clone on Linux — which the CI matrix includes — gets
`cassini/`, and `from spyceman.hosts import Cassini`, the form the README uses, fails
there. This is unchanged from the previous review and remains the most likely cause of a CI
failure that looks unrelated to any code change.

### 12.3 Documentation now describes a tool that no longer exists

> **Fixed 2026-08-17.** `CLAUDE.md` and the `pyproject.toml` comment were repointed at
> `programs/ktupler.py` when the tool was found there (§1.7). The last stale reference
> was inside the tool itself -- its banner read `# spyceman/ktupler.py` and its two
> usage lines read `python ktupler.py` -- and those are now correct as well.


`CLAUDE.md:94` and `pyproject.toml:115` both point at `src/spyceman/ktupler.py`. See §1.7.

### 12.4 Two docstrings fall outside the project standard

> **Half fixed 2026-08-16.** `_get_spicepath()` gained its `Returns:` and `Raises:`
> sections while §9.1 was being fixed. The over-width line in
> `hosts/Cassini/_TOUR_SPKS_V3.py` remains; it is in a generated table.

Of 275 functions, all but one satisfy the `Parameters:`/`Returns:`/`Raises:` standard
recorded in `.claude/rules/docstrings.md`:

- `_localfiles.py:54` — `_get_spicepath()` returns a value and has no `Returns:` section.
- `hosts/Cassini/_TOUR_SPKS_V3.py:661` — one line of 91 columns.

### 12.5 There is still no test suite

> **Fixed 2026-08-17.** There is now a suite of 271 tests that runs in under three
> seconds, plus 7 opt-in slow ones. `tests/test_layout.py` keeps the parse checks and
> loses its docstring claiming the package cannot be imported, which is no longer true.
> Three files are new:
>
> `tests/test_import.py` -- imports each of the fifteen core modules individually,
> checks that every name in `__all__` is reachable and that `__all__` lists nothing
> else, and pins the two environment behaviors that have bitten: that importing the
> package does not require SPICEPATH, and that `walk()` without it warns rather than
> raising (§1.6). This is the test that would have caught §1.2 and §1.3 the moment they
> were introduced.
>
> `tests/test_utils.py` -- 60 cases over `_input_set`, `_input_list` and
> `_test_version`, chosen around the distinctions those functions actually draw: that
> zero is a value and not an empty input, that only a *list* of two is a range while a
> tuple or set of two is not, that a tuple is a single version (version 1.5, not the set
> {1, 5}), and that an incomparable version is a non-match rather than an error (§11.4).
>
> `tests/test_docstrings.py` -- enforces the project docstring standard structurally
> over every function in the package: a docstring must exist, parameters must appear
> under `Parameters:` and match the signature exactly in both directions, a parameter
> defaulting to `None` must be marked `optional`, `Returns:` must be present exactly
> when the function can return or yield a value, and no line may exceed 90 columns. It
> found two live violations, both now fixed: the closure in `recipe.py` built by
> `_wrap_func` had no docstring in the source (it inherits one at runtime from
> `functools.update_wrapper`, which an AST-based check cannot see), and
> `_TOUR_SPKS_V3.py` line 661 carried one stray leading space that pushed it to 91
> columns -- the identical line five rows above it is 90. That edit was confirmed
> whitespace-only by comparing the parsed AST before and after.
>
> `tests/test_hosts_slow.py` -- imports of the full kernel catalogs, marked `slow` and
> deselected by default via `addopts`. See §12.6 for why they have to be opt-in.


`tests/test_layout.py` checks only that the package is laid out as the packaging config
claims and that every module parses — and note that it now passes while three modules raise
`NameError` the moment they are executed, because parsing is not importing. Extending it to
attempt an import of every module would have caught §1.2 and §1.3 immediately, and is worth
doing before anything else in this document.

---

### 12.6 Importing a host catalog takes minutes — **new, found 2026-08-17**

> **Fixed 2026-08-17** by candidate 1 below, memoization. Measured after the change:
>
> | Import | Before | After | Speedup |
> | --- | --- | --- | --- |
> | `spyceman` | 0.8 s | 0.6 s | — |
> | `spyceman.hosts.Voyager` | 25.6 s | 0.9 s | 28× |
> | `spyceman.hosts.Cassini` | 141 s | 5.0 s | 28× |
>
> The memoization lives in `_cspyce.py` rather than `_utils.py`, for two reasons. It is the
> module that owns the `CSPYCE` indirection, so it can wrap both the readers and the
> mutators without the import cycle that `_utils` would create; and it already reassigns
> `bodn2c`, `bodc2n`, `cidfrm`, `namfrm` and `frmnam` for a related reason, so this is the
> established place for adjustments to CSPYCE's behavior. Nothing in `_utils`,
> `_kernelinfo` or `kernel.py` changed.
>
> `CSPYCE.get_body_aliases()` and `CSPYCE.get_frame_aliases()` are wrapped to consult a
> dict keyed by the item; misses are cached too, since a miss is the expensive case.
> Every function that can change SPICE's body or frame tables — `define_body_aliases`,
> `define_frame_aliases`, `boddef`, `furnsh`, `unload`, `kclear`, `clpool`, `ldpool`,
> `pdpool`, `pcpool`, `pipool` — is wrapped to clear the caches in a `finally`, so a call
> that raises partway still invalidates. `clear_alias_caches()` is available for a caller
> that alters the tables without going through `CSPYCE`.
>
> Two hazards were specifically closed. Each call returns *new* lists rather than the
> cached objects, so a caller mutating a result cannot corrupt the cache — the four call
> sites in `_utils` are read-only today, but `CSPYCE` is re-exported from
> `spyceman/__init__.py` and external callers are not bound by that. And the wrapped
> `furnsh`/`unload` cost nothing in practice: furnishing consults `naif_ids` values already
> stored on the `_KernelInfo` objects, so dropping the cache there does not cause any
> re-resolution.
>
> **Verified by equivalence, not just by speed.** Both catalogs were imported twice in
> separate processes — once normally, once with `CSPYCE.get_body_aliases` and
> `get_frame_aliases` restored to the unwrapped `cspyce.alias_support` originals — and the
> resolved `_naif_ids`, `_naif_ids_as_found` and `_naif_ids_wo_aliases` of every catalogued
> kernel were dumped and compared. 336 Voyager kernels and 1,930 Cassini kernels: identical
> in every field. `tests/test_cspyce.py` adds 25 tests covering the invalidation on each
> kind of mutation, the copy-on-return, and agreement with the unwrapped originals.
>
> Candidate 2, lazy resolution, was not pursued. It is the better answer in principle,
> because it would make the import cost proportional to what is actually used rather than
> merely cheap, but it changes when `set_info()`'s work happens and so is a behavioral
> change; memoization is transparent and provably equivalent. The `slow` marker on
> `tests/test_hosts_slow.py` is kept, because five seconds is still too slow for the
> default suite.

Measured on an Apple-silicon Mac, with the package already imported:

| Import | Wall clock |
| --- | --- |
| `spyceman` | 0.8 s |
| `spyceman.hosts.Voyager` | 25.6 s |
| `spyceman.hosts.Cassini` | 141 s |

A `cProfile` run over the Voyager import accounts for it precisely. Of 34 seconds under
the profiler, **32.1 seconds is `cspyce._cspyce0.sigerr`**, called 30,555 times:

```text
   ncalls  tottime  cumtime  filename:lineno(function)
       10    0.001   33.415  kernelfile.py:190(set_info)
      293    0.001   32.343  _kernelinfo.py:536(naif_ids)
    30555   32.135   32.135  {built-in method cspyce._cspyce0.sigerr}
13665/10425  0.035   28.568  cspyce/alias_support.py:50(get_frame_aliases)
```

The chain is: each module calls `KernelFile.set_info()` once per `KTuple`; the `naif_ids`
setter calls `naif_ids_with_aliases()` and then `naif_ids_wo_aliases()`; each of those
calls `CSPYCE.get_frame_aliases(naif_id)` and `CSPYCE.get_body_aliases(naif_id)` for every
ID; and every ID that is *not* a frame makes SPICE signal an error, which costs on the
order of a millisecond. A spacecraft body ID such as `-82` is not a frame, so the common
case is the slow one:

```text
get_frame_aliases(   -82) -> []          0.193 ms
get_frame_aliases(   699) -> [10016]     0.070 ms
```

Cassini's catalog holds 1,764 `KTuple`s, each naming on the order of thirty NAIF IDs, and
the same handful of IDs recurs across nearly all of them. The work is almost entirely
repeated.

Note that `_cspyce.py` already anticipates this class of problem — it reassigns
`bodn2c`, `bodc2n`, `cidfrm`, `namfrm` and `frmnam` to their `.flag` variants precisely to
"disable Python errors for a few core functions". That does not help here, because
`cspyce.alias_support.get_frame_aliases()` calls `cidfrm_error` and `frmnam_error`
internally, bypassing the module-level names spyceman replaced.

Two candidate fixes, neither applied:

1. **Memoize the alias lookups.** NAIF ID → aliases is a pure function of the loaded alias
   tables, and the tables change only through `define_body_aliases()` and
   `define_frame_aliases()`. Caching in `_utils` and clearing the cache from wrappers
   around those two functions would collapse ~180,000 lookups to a few dozen. The
   correctness risk is a stale entry, and it is real: `hosts/Voyager/__init__.py` and
   `solarsystem/{Jupiter,Neptune,Saturn}.py` all define aliases at import time, so the
   invalidation has to be right.
2. **Do the work lazily.** `set_info()` resolves aliases for every catalogued kernel
   whether or not that kernel is ever selected. Deferring resolution until a file's
   `naif_ids` is actually read would make the import cost proportional to what is used.

Candidate 1 was applied; see the status note above.

---

### 12.7 The package reported no `__version__`

> **Fixed 2026-08-17**, while writing the §12.5 import tests.

`setuptools_scm` is configured with `write_to = "src/spyceman/_version.py"` and duly
generates that file, but nothing imported it, so `spyceman.__version__` did not exist.
`src/spyceman/__init__.py` now ends with the same idiom the sibling `rms-polymath` uses:

```python
try:
    from ._version import __version__
except ImportError:                         # pragma nocover
    __version__ = 'Version unspecified'
```

---

### 12.8 Release dates are parsed with a general-purpose grammar — **new, found 2026-08-17**

> **Fixed 2026-08-17.** Found by re-profiling after §12.6, when the alias lookups stopped
> dominating and this became 80% of what remained.

Once §12.6 removed the alias-lookup cost, a fresh profile of the Cassini import showed the
bottleneck had moved rather than disappeared:

| Path | Cumulative | Share |
| --- | --- | --- |
| `release_date` setter → `julian.day_sec_from_string` | 8.24 s | 80% |
| `naif_ids` setter | 0.23 s | 2.2% |

Every `KTuple` release date is a plain `'2020-02-12'`, but `validate_release_date()` sent
each one through `julian`'s general-purpose parser, which is built on `pyparsing`: 2,917
calls at about a millisecond each, 739,205 `_parseNoCache` invocations, a third of that
merely re-`streamline()`-ing the grammar. The asymmetry was visible in the code already —
the `time` setter used the ISO-specific `julian.tdb_from_iso()`, while the neighboring
`release_date` setter used the general parser for data that is always ISO.

`_utils._fast_day_sec_from_iso()` now recognizes `YYYY-MM-DD` and
`YYYY-MM-DDTHH:MM:SS.fff` — `T` or a space — and returns `None` for anything else, so the
caller falls back to `julian` and raises exactly the exception it raised before. Measured
per call: 0.0038 ms against 0.9591 ms.

**Field values are trusted, not checked**, on the maintainer's instruction that catalog
dates are machine generated and therefore always well formed. This is worth stating
explicitly because `julian.day_from_ymd()` performs no validation of its own: it rolls an
impossible date into the following month, so `validate_release_date('2019-02-29')` now
returns `'2019-03-01'` where it previously raised. The same date written `'2019/02/29'`
still raises, because that shape is not recognized and reaches `julian`. Both behaviors are
pinned by tests so the asymmetry is a known property rather than a surprise.

An earlier revision validated by converting the day number back with
`julian.ymd_from_day()` and declining on a mismatch, which deferred every calendar rule to
`julian` — including the ten days the Gregorian reform of October 1582 skipped. It was
removed as unnecessary. For the record, it was not costing anything measurable: the guard
benchmarked at 0.0065 ms per call, but removing it moved the Cassini import only from
1.27 s to a 1.26–1.35 s spread, i.e. within run-to-run noise. The simplification is to the
code, not to the clock.

The hyphens in the pattern are required rather than optional. Without validation an
unhyphenated form would read any eight digits as a date — `'12345678'` as the 78th day of
the 56th month of 1234 — and no catalog anywhere in the package writes a date without
hyphens, so allowing it would have bought nothing.

The same fast path is shared by `validate_time()` and by a new `validate_iso_time()`, which
replaces the four direct `julian.tdb_from_iso()` calls in `_kernelinfo.py`, `rule.py` and
`kernel.py`. `validate_iso_time()` keeps `tdb_from_iso` as its fallback rather than the
general parser, so those call sites stay exactly as strict as they were — `'2020/02/12'` is
still rejected there, as the test asserts.

Import times, with §12.6:

| Import | Original | After §12.6 | After §12.8 |
| --- | --- | --- | --- |
| `spyceman` | 0.8 s | 0.6 s | 0.54 s |
| `spyceman.hosts.Voyager` | 25.6 s | 0.9 s | 0.50 s |
| `spyceman.hosts.Cassini` | 141 s | 5.0 s | **1.27 s** |

Verified the same way as §12.6, by equivalence rather than by speed. The contract now
has two halves, and both are checked: for a date that exists the fast path must return
exactly what `julian.day_sec_from_string()` returns, and for a string of any other shape it
must return `None` so the caller falls back. 8,092 valid date and date-time strings — every
day of eleven representative years, the cross-product of hour, minute and second values,
and both real leap seconds — produced no mismatch, and every unrecognized shape still
declined. Both catalogs were then imported twice, once with `_fast_day_sec_from_iso` forced
to return `None`, and the release date, time range and NAIF IDs of all 2,266 kernels
compared: identical, and identical to the baseline taken before any of this work.
`tests/test_dates.py` adds 51 tests.

---

## Recommended priorities

**Every finding in this document is now closed.** The steps below were the plan as
originally written; each is recorded here with what actually happened, because the order
mattered and two of the steps had to be resequenced.

**Step 1 — close the four new import-time breakages.** Done: §1.1 through §1.4, plus the
deletion of the `per-file-ignores` in `pyproject.toml`. Ruff was disabled outright rather
than gated on `--select F`, at the maintainer's direction; re-enabling it means restoring
all three switches named in §12.1.

**Step 2 — add an import test.** Done, though later than planned: it landed as §12.5, after
the library could actually be imported. The prediction held — a test that imports every
module would have caught three of the four fatal defects, and the equivalent test now
exists in `tests/test_import.py`.

**Step 3 — repair `Rule`.** Done: §5.1 through §5.12. The bare `except` narrowing (§11.4)
was done first, as recommended, and it did make the rest verifiable. One claim in §5.1 was
withdrawn during the work: the tag-ordering hazard turned out not to exist.

**Step 4 — repair `_KernelInfo`.** Done: §4.1 through §4.10, with the three registries
unified behind `register()`/`lookup()` (§11.2). The prediction that fixing §4.2 alone would
only move the failure to §1.1 was correct.

**Step 5 — repair `Kernel` and `KernelFile`.** Done: §6.1 through §6.21, in the order
suggested. `basenames` (§6.5) did unblock a large fraction of the rest, and fixing it
immediately exposed §6.19, which the infinite recursion had been masking.

**Step 6 — everything in §7 through §10.** Done. The guess that some defects would dissolve
once the lower layers worked was half right: none dissolved, but several changed direction.
§8.2 was resolved by moving the signature rather than the readers, because by the time it
was reached fifteen call sites had established the plural spelling.

Both of the out-of-sequence items are also closed. The `cassini`/`Cassini` case mismatch is
fixed (§12.2). The `SPICEMODULE`/`spicepy` question is **still open and still a decision for
the maintainer**: `_kernelinfo.py` imports `cspyce` directly rather than going through
`CSPYCE`, and the fake alias functions in `_cspyce.py` have never executed. Either make the
fallback real and test it, or delete about forty lines that cannot currently run.

### What to do next

The document is closed, but the codebase is not finished. In rough order of value:

1. ~~**Behavioral tests for kernel selection.**~~ **Done 2026-08-17.**
   `tests/test_selection.py` covers which kernels a generated selection function chooses —
   time windows, NAIF IDs, basename and version and release-date constraints, exclusion,
   precedence order, and the shape of the returned Kernel. `tests/test_furnish.py` covers
   what is actually loaded and in what order, using `Kernel.debug(True)` so nothing reaches
   SPICE or the network. Shared fixtures live in `tests/conftest.py`, which manages the two
   pieces of global state that would otherwise make these order-dependent: `_KernelInfo`'s
   process-wide basename registry, and the module-level furnish record and switches.

   The tests were validated by mutation rather than by passing. Four defects were
   reintroduced one at a time and the suite was re-run each time: reverting the §6.20 guard
   (3 tests caught it), making `exclude` keep the lowest-precedence file instead of the
   highest (1), dropping the exclusion of unselected files (1), reversing the furnish order
   (4), and disabling time and ID filtering (8). None escaped.

   Two of the tests were wrong on first writing, and both errors were mine rather than the
   library's: an LSK required by an SPK is a *co*requisite, not a prerequisite, because
   precedence only orders kernels of one ktype; and an exclusion belongs to a Kernel object
   rather than to a basename, which is how a selection function attaches one to the result
   it returns. Both distinctions are now tests in their own right. A third test passed for
   the wrong reason — it used `ids=499` against an all-IDs kernel, which `id_overlap()`
   already handled, so it never reached the §6.20 guard at all; the guard only fires when
   *both* sides are empty. It was rewritten, and the mutation run is what exposed it.

   `fail_under` and the `codecov.yml` project target are raised from 0 to 30, against an
   actual 35.5%. Both are floors that catch a collapse rather than targets.
2. ~~**Re-enable ruff, starting from `select = ["F"]`.**~~ **Done 2026-08-17.** Switched
   on in all three places, with `select = ["F"]`. `ruff format` stays off deliberately:
   the house style is column-aligned and the formatter would reflow it.

   F found four things, and one was a live defect **introduced by the §11.4 fix in this
   very review**: `_kernelinfo.py` calls `warnings.warn()` in the comment-reading fallback,
   but the module never imported `warnings`, so that branch raised `NameError` instead of
   warning. Exercising the branch afterward turned up a second fault on the same line that
   no linter could see — it interpolated `self.basename`, and `_KernelInfo` has only
   `_basename`. Both are fixed and `tests/test_kernelinfo.py` now covers the path with a
   deliberately corrupt kernel. The other three findings were unused imports, two of them
   left behind by the §12.8 change that replaced `julian.tdb_from_iso` with
   `validate_iso_time`.

   That is the argument for F in one example: a defensive branch nobody had run, a bug
   introduced while fixing another bug, and static analysis catching it in the second it
   was enabled.

   The wider set was measured and not adopted. `E,W,I,UP,B,SIM,C4,A,N,PT,RUF` reports 177
   further findings, and the four largest groups describe the house style rather than
   defects: E402 (21, deliberate mid-file imports), I001 (24, which would reorder the
   column-aligned import blocks), N999/N801/N802 (16, the capitalized host and body modules
   and lowercase descriptor classes), RUF012 (7, the class-level registries in
   `_KernelInfo`). Adding any category means fixing or ignoring its findings first. The
   candidates that look like genuine smells are B904 (2), B006 (7), B028 (9) and E741 (2).
3. **Decide the `spicepy` question** above, and either exercise or remove that path.
4. ~~**Consider lazy NAIF ID resolution**~~ (candidate 2 in §12.6). **Withdrawn
   2026-08-17.** Profiling after §12.6 and §12.8 shows ID resolution is now 2.2% of the
   Cassini import, so making it lazy would save about a tenth of a second. The design was
   worked out before this was measured, and is recorded here only because it turned up a
   genuine bug that should be fixed on its own: `_manual_defs` records the alias-expanded
   `_naif_ids`, and `replace()` replays it by writing that private field directly, leaving
   `_naif_ids_as_found` and `_naif_ids_wo_aliases` unset. Confirmed by experiment —
   `naif_ids_as_found` returns `None` after a `replace()`, and the metakernel branch of the
   `naif_ids` getter does `naif_ids |= lookup(basename).naif_ids_as_found`, which raises
   `TypeError` on `None`. Recording the as-found set instead of the expanded one fixes it.
5. **Bring `programs/` under the checks.** §1.7 and §10.7 are the same story twice: the
   generator that emits 13,600 lines of data is neither linted nor tested, and it has
   already put one unparseable date into the tables.
