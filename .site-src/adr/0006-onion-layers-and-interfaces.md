# ADR 0006: Onion layers, interfaces and one class per file

Status: accepted and implemented (see "As built")

## Context

The package grew in two halves. The orchestration half (`services`, `controllers`, `repositories`,
`infrastructure`, `interaction`, `runtime`) follows an onion, with one class per file and ABC
interfaces in sibling `interfaces/` folders. The packaging half (`publishing/`, 138 files, 6,386 of the
10,229 lines) is a single flat layer: 119 plain classes, models, services and adapters mixed,
no interfaces, and a controller that imports 21 concrete classes. Several layers also break their
own rules: composition happens in services, controllers and transports, and the architecture test
forbids `domain` from importing `errors`, which is backwards for the innermost ring.

The model-backed stages of ADR 0003 will add as much code again. They need the rules to be
mechanical before they arrive, not after.

## Decision

### Layers, innermost first

| Layer | Holds | May import |
|---|---|---|
| `errors` | exception classes | standard library |
| `models` (was `domain`) | entities and value objects, enums | `errors`, standard library |
| `contracts` | wire and config schemas (pydantic) | `errors`, `models`, pydantic |
| `interfaces` | ports shared across layers | standard library and other interfaces at run time; `errors`, `models`, `contracts` only under `TYPE_CHECKING` |
| `services` | use cases and policy | the layers above, plus pure-compute libraries (numpy, markdown-it-py, defusedxml) |
| `controllers` | one entry point per capability | the layers above, `services` |
| `repositories` | persistence, project files and sources | the layers above, `services.interfaces`; database and file libraries |
| `infrastructure` | adapters to tools, networks, images, PDFs, archives | the layers above, `services.interfaces`; any effectful library or process |
| `interactions` (was `interaction`) | transports: REST, MCP, CLI, webhooks in | `controllers`, the layers above, `services.interfaces`; transport libraries |
| `runtime` | the composition root | everything |

- Dependencies point inward. Only `runtime` constructs concrete classes from more than one layer.
- Effectful libraries (PIL, pypdf, pdfplumber, reportlab, subprocess, zipfile, entry points, git,
  clocks, file reads and writes) never appear in `models`, `contracts` or `services`. A service that
  needs one depends on an interface and an adapter in `infrastructure` or `repositories` provides it.
- `publishing/` is split across these layers. Its subpackage names (`epub`, `covers`, `typesetting`,
  `qa`, `release`) become folders inside the layers; its top-level modules go under `publishing/`.
- `errors` is innermost. Models may import errors; the old rule that forbade it is removed.

### Interfaces

- Every folder, including every new subfolder, has an `interfaces/` folder. `interfaces/` packages and
  `assets/` are exempt, and so is `infrastructure/migrations/` (see "As built").
- One class per file. `x/foo.py` defining `Foo` is paired with `x/interfaces/foo_interface.py`
  defining `FooInterface`, and `Foo` inherits it.
- An interface is an ABC with `__slots__ = ()` that declares **methods only**, never fields or
  abstract properties. Fields would change what pydantic and dataclasses generate.
- Dataclasses, pydantic models, SQLModel tables and exceptions inherit their ABC interface; this was
  checked to leave `model_fields`, the OpenAPI schema and table metadata unchanged.
- **Enums use a protocol, not an ABC.** `Enum` and `ABC` have conflicting metaclasses and mypy does not
  catch it. An enum gets a `runtime_checkable` `Protocol` and a test that checks the enum against it.
- A class that already implements a top-level interface in `interfaces/` satisfies the rule. The 20
  `*Port` classes there are renamed `*Interface`.
- Interface modules import only the standard library and other interfaces at run time. Types from
  `models`, `contracts` and `errors` come in under `TYPE_CHECKING` with
  `from __future__ import annotations`, so signatures stay exact and mypy still checks overrides.

### Public API

The cover-plugin API is public: entry-point group `engineering_influence.covers`, and the `books`
repository imports 17 classes by their deep paths: 13 in its cover scripts, and `CoverBuilder`,
`CoverPluginLoader`, `PainterRegistry` and `ProjectLayout` in its README (R0 counted only the 13;
R3 corrected it). A façade `engineering_influence.covers` re-exports the cover classes with an
`__all__`; `ProjectLayout`, a model, keeps a deprecated shim at its old path. The old `engineering_influence.publishing.covers.*` paths stay as
shims that re-export the same class objects (the loader checks `isinstance(plugin, CoverPlugin)`) and
emit a one-time `DeprecationWarning`, for one minor release (ADR 0004). The entry-point group does not
change. These classes keep their names even where they do not end in `Interface`.

### Method

- `scripts/refactor/move_map.toml` is the plan of record: for every class, where it lives, where it goes,
  its interface and why. A pull request that moves or reclassifies a class edits its entry. An
  architecture test keeps the map complete against the tree.
- `scripts/refactor/inventory.py` reports the facts the map is built from.
- Rules arrive as **ratchets**: `tests/architecture/ratchet.json` records how many violations each rule
  has today. A rule can only improve, and the test fails if a count rises, or falls without the file
  being lowered. Each restructuring PR lowers counts; the last one makes every count zero and the rules
  strict.
- Moves use `git mv` and a codemod that rewrites imports everywhere, including strings that name
  modules. No behaviour changes. Every restructuring PR must keep the test count, 100% coverage, the
  OpenAPI document, the CLI help, the MCP tool list and the fixture book's structural snapshot
  (`tests/fixtures/fixture_book/expected/snapshot.json`) unchanged.
- Feature work on `publishing/` and the layers being moved pauses while the restructure is in flight.

## Consequences

- A reader can predict where a class lives and what it may import, and CI can check it.
- Roughly 240 new interface files exist. They are generated, and the ratchets stop them drifting from
  their classes.
- Test doubles become real implementations of the interfaces, which replaces the `monkeypatch.setattr`
  calls that patch production classes (33 `setattr` calls today, some of them on `sys`).
- Moving every class changes every import path. The public cover-plugin paths are protected by shims;
  everything else is internal.

## As built

The restructure shipped as pull requests R0 to R13 (`changelog.d/m1-r*.md` has one entry for each).
Four things differ from the plan above, and the plan is left as written so the difference is visible:

- **The ratchets were retired.** The plan lowered counts in `tests/architecture/ratchet.json` until
  every rule reached zero. They did, so R11 deleted the file and `test_rules.py` now asserts that each
  of nine metrics is zero everywhere and that none has been dropped. A violation fails the build; it
  is not recorded.
- **The cover-plugin shims were removed in R11, with no deprecation window.** `publishing.covers.*` and
  `publishing.project_layout` re-exported the real classes for a time, then were deleted. ADR 0004
  lets a minor version before 1.0 break a contract if the changelog says so, and the R11 entry is
  marked **Breaking**. The names live on in the `engineering_influence.covers` facade.
- **Test doubles replaced the patches.** The plan counted 33 `monkeypatch.setattr` calls. R12 and R13
  injected fakes through constructors, and `tests/architecture/test_no_patching.py` now permits only
  standard-library calls at the system boundary (`subprocess.run`, `sys.argv`, `sys.path`,
  `zipfile.ZipFile.testzip`) and one class a test defines. A new patch of anything else fails the
  build, and a boundary entry no test uses any more fails it too.
- **Some pure helpers are still built where they are used.** `PublishingController` builds its audit
  classes and `EpubVerifier` builds its own checks, because no test has to replace them. Anything a
  test replaces, and every adapter, is injected.
- **Alembic migrations are exempt from the file rules.** An Alembic script is a module of functions
  and constants by contract (`upgrade()`, `downgrade()`, `revision`), so `infrastructure/migrations/`
  is excluded from the one-class-per-file, no-loose-function, interface-folder and layer-matrix checks
  through `SCRIPT_FOLDERS` in `tests/architecture/architecture_metrics.py`. The exemption names that
  folder and nothing else. The scripts are still linted, type-checked with `mypy --strict` and run by
  the tests, which also compare the schema they build with the SQLModel models, so a model change
  without a migration fails the build. The class that drives them, `SchemaMigrator`, follows every
  rule.
