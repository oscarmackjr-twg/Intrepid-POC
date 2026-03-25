# Phase 16: Linting - Research

**Researched:** 2026-03-25
**Domain:** ESLint v9 (flat config), ruff, husky, lint-staged, GitHub Actions CI
**Confidence:** HIGH

## Summary

Phase 16 is a well-scoped tooling phase with no ambiguity in the decision space. All ESLint packages are already installed in `frontend/node_modules` at the correct versions; the only missing artifact is the `eslint.config.js` file itself. The ruff violation is exactly one unused import in `backend/tests/test_tagging_allocation.py`. Husky and lint-staged are not yet installed and must be added to `frontend/devDependencies`.

The flat config format (ESLint v9) requires `eslint.config.js` to export a default array of config objects rather than the old `.eslintrc` style. The installed `typescript-eslint` v8 exposes a `tseslint.config()` helper that wraps this pattern cleanly. The CI step is a straightforward insertion into the existing `security-quality-gate` job immediately after the `npm audit` step that already runs `npm ci`.

**Primary recommendation:** Follow decisions D-01 through D-14 exactly. No research gaps; every implementation detail is deterministic from the installed package versions and existing CI structure.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Create `frontend/eslint.config.js` with minimal ruleset only — react-hooks + react-refresh plugins
- **D-02:** Use the packages already installed: `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals`
- **D-03:** No TypeScript strict rules — keep zero new violations at the point of setup
- **D-04:** Config must make `npm run lint` (which runs `eslint .`) pass cleanly
- **D-05:** Add `npm run lint` as a blocking step in `.github/workflows/deploy-test.yml`
- **D-06:** The step runs inside the frontend directory (`working-directory: frontend`)
- **D-07:** Runs `npm ci` before linting (install deps first)
- **D-08:** Add `husky` and `lint-staged` to frontend devDependencies
- **D-09:** lint-staged config: run `eslint --fix` on staged `*.ts` and `*.tsx` files
- **D-10:** lint-staged config: run `ruff check --fix` on staged `*.py` files (from backend/)
- **D-11:** `prepare` script in `frontend/package.json` to install husky hooks on `npm install`
- **D-12:** Pre-commit hook file at `.husky/pre-commit` running `npx lint-staged`
- **D-13:** Fix the 1 existing ruff violation (unused import) — use `ruff check --fix backend/`
- **D-14:** No changes to `backend/pyproject.toml` ruff config (existing config is correct)

### Claude's Discretion

- Exact `eslint.config.js` syntax (flat config format required for ESLint v9)
- Which files/directories to ignore in ESLint config (node_modules, dist)
- Whether to place `lint-staged` config in `package.json` or `.lintstagedrc`

### Deferred Ideas (OUT OF SCOPE)

- Prettier / auto-formatting for frontend
- TypeScript strict ESLint rules (typescript-eslint/recommended-type-checked)
- Expanding ruff rules (isort, bugbear, naming)
- mypy config tightening
</user_constraints>

---

## Standard Stack

### Core (already installed)

| Library | Installed Version | Purpose | Notes |
|---------|------------------|---------|-------|
| `eslint` | 9.39.2 | JavaScript/TypeScript linter | Flat config only (v9+) |
| `@eslint/js` | 9.39.2 | ESLint's built-in JS recommended rules | Provides `js.configs.recommended` |
| `typescript-eslint` | 8.53.1 | TypeScript parser + rules | v8 unified package; exposes `tseslint.config()` helper |
| `eslint-plugin-react-hooks` | 7.0.1 | Enforces Rules of Hooks | Required for React correctness |
| `eslint-plugin-react-refresh` | 0.4.26 | Validates HMR-safe component exports | Required by Vite dev setup |
| `globals` | 16.5.0 | Standard browser/node global variable sets | Used in `languageOptions.globals` |

### To Install (new packages)

| Library | Latest Version | Purpose | Location |
|---------|---------------|---------|----------|
| `husky` | 9.1.7 | Git hooks manager | `frontend/devDependencies` |
| `lint-staged` | 16.4.0 | Run linters on staged files only | `frontend/devDependencies` |

**Installation (from frontend/ directory):**
```bash
npm install --save-dev husky lint-staged
npx husky init
```

**Version verification:** Confirmed against npm registry on 2026-03-25.
- `husky@9.1.7` — current latest stable
- `lint-staged@16.4.0` — current latest stable

---

## Architecture Patterns

### ESLint v9 Flat Config Format

ESLint v9 dropped `.eslintrc.*` entirely. The config file must be named `eslint.config.js` (or `.mjs`/`.cjs`) and export a default array of config objects.

**Pattern: `frontend/eslint.config.js`**
```javascript
// Source: typescript-eslint v8 docs + eslint.org/docs/latest/use/configure/configuration-files
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'node_modules'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
    },
  },
)
```

This is the canonical Vite-generated template for ESLint v9 + typescript-eslint v8 + React. The `tseslint.config()` helper is a thin wrapper that returns the array — it accepts spread objects and correctly handles the `extends` array syntax.

**Key requirement:** `frontend/package.json` has `"type": "module"`, so `eslint.config.js` uses ESM import syntax (not `require()`). This is correct as shown above.

### husky + lint-staged Pattern

**`.husky/pre-commit`** (created by `npx husky init`, then edited):
```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npx lint-staged
```

Husky v9 changed init: `npx husky init` creates `.husky/pre-commit` with a sample command. The `_/husky.sh` sourcing pattern still works in v9. The `prepare` script must be added to `package.json`:

```json
"scripts": {
  "prepare": "husky"
}
```

**lint-staged config placement:** Recommend `package.json` (inline) — keeps all frontend config in one file. The `lint-staged` key at the top level of package.json is the standard placement:

```json
"lint-staged": {
  "*.{ts,tsx}": "eslint --fix",
  "backend/**/*.py": "ruff check --fix"
}
```

Note: lint-staged runs from the `frontend/` directory (where `package.json` lives). The `backend/**/*.py` glob resolves relative to the git repo root only if lint-staged v10+ is used with `--relative` or absolute paths — see Pitfall 3 below for the correct approach.

### CI Insertion Point

The ESLint step goes into `security-quality-gate` job after the existing `npm audit` step (line 59 in current `deploy-test.yml`). The `npm ci` is already run by the audit step — the ESLint step can reuse that or run its own. Per D-07, it should include its own `npm ci` to be self-contained.

**New CI step YAML:**
```yaml
- name: ESLint (frontend)
  working-directory: frontend
  run: |
    npm ci
    npm run lint
```

Insert after the `npm audit` step and before `Setup Terraform`.

### Ruff Fix

The single violation is in `backend/tests/test_tagging_allocation.py` line 7: `import pytest` is unused.

```bash
ruff check --fix backend/
```

This auto-removes the import. The file still compiles and tests still pass (pytest is used via test discovery, not explicit import).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git pre-commit enforcement | Custom shell script checking staged files | husky + lint-staged | lint-staged handles partial-file staging, stash/unstash, parallel execution |
| ESLint config boilerplate | Writing config from scratch | typescript-eslint's `tseslint.config()` helper | Handles flat config array construction, extension merging correctly |

---

## Common Pitfalls

### Pitfall 1: ESM vs CJS in eslint.config.js

**What goes wrong:** Using `module.exports =` (CommonJS) in `eslint.config.js` when `package.json` has `"type": "module"`.

**Why it happens:** Old tutorials show `.eslintrc.js` with `module.exports`. The v9 flat config file must match the package's module type.

**How to avoid:** Since `frontend/package.json` has `"type": "module"`, use ESM `import`/`export default` syntax in `eslint.config.js`. If CJS is needed, name the file `eslint.config.cjs`.

**Warning signs:** `SyntaxError: Cannot use import statement in a module` or `module is not defined` errors when running `eslint`.

### Pitfall 2: tseslint.configs.recommended vs recommended-type-checked

**What goes wrong:** Using `tseslint.configs.recommended-type-checked` requires `parserOptions.project` pointing to `tsconfig.json`. If that tsconfig path is wrong, ESLint crashes.

**Why it happens:** The "type-checked" config adds rules requiring TypeScript's type information, which needs the tsconfig.

**How to avoid:** Per D-03, use `tseslint.configs.recommended` only (no type-checking). This is explicitly out of scope.

**Warning signs:** Error message containing `You have used a rule which requires type information but don't have parserOptions.project configured`.

### Pitfall 3: lint-staged glob for backend Python files

**What goes wrong:** `"backend/**/*.py": "ruff check --fix"` in `frontend/package.json` — lint-staged passes absolute paths to the command but the glob is matched against absolute paths from the repo root.

**Why it happens:** lint-staged v10+ passes absolute file paths. The glob `backend/**/*.py` is matched against absolute paths, so it correctly filters files under `backend/`. However, `ruff check --fix` must receive file paths it can resolve — since ruff is run from wherever lint-staged is invoked (frontend/), the path resolution must be verified.

**How to avoid:** Use `"../backend/**/*.py"` or test with a staged Python file before finalizing. Alternatively, place lint-staged config in the repo root `.lintstagedrc` with separate patterns. The simplest approach: use `"**/*.py": "ruff check --fix"` and rely on `backend/pyproject.toml` exclude list to skip non-backend Python files.

**Warning signs:** `ruff check --fix: No Python files found` or linting wrong files.

### Pitfall 4: husky v9 init vs v8 behavior

**What goes wrong:** Older tutorials show `npx husky add .husky/pre-commit "npx lint-staged"` — this command was removed in husky v9.

**Why it happens:** husky v9 simplified the API. The `add` subcommand no longer exists.

**How to avoid:** Use `npx husky init` to scaffold, then manually edit `.husky/pre-commit` to contain `npx lint-staged`.

**Warning signs:** `husky: command not found: add`.

### Pitfall 5: prepare script runs on CI

**What goes wrong:** The `prepare` script (`husky`) runs automatically on `npm ci` in CI, but husky v9 skips itself when `CI=true` environment variable is set.

**Why it happens:** husky v9 added built-in CI detection — if `CI` env var is truthy, `husky` exits 0 without installing hooks. GitHub Actions sets `CI=true` automatically.

**How to avoid:** No action needed — this just works. Document it so the planner does not add a `HUSKY=0 npm ci` workaround that is unnecessary.

---

## Code Examples

### Complete eslint.config.js (Vite/React/TypeScript project)

```javascript
// frontend/eslint.config.js
// Source: typescript-eslint v8 + ESLint v9 flat config docs
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'node_modules'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
    },
  },
)
```

### lint-staged config in package.json

```json
"lint-staged": {
  "*.{ts,tsx}": "eslint --fix",
  "**/*.py": "ruff check --fix"
}
```

### .husky/pre-commit content

```sh
npx lint-staged
```

(husky v9 no longer needs the `_/husky.sh` shim sourced in the pre-commit file for most setups. The simplified single-line form is the current recommended pattern per husky v9 docs.)

### CI step (deploy-test.yml insertion)

```yaml
      - name: ESLint (frontend)
        working-directory: frontend
        run: |
          npm ci
          npm run lint
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `.eslintrc.js` / `.eslintrc.json` | `eslint.config.js` (flat config) | ESLint v9.0.0 (April 2024) | Must use array export; `extends` array replaced with `...tseslint.configs.recommended` spread |
| `husky add .husky/pre-commit "cmd"` | `npx husky init` + manual file edit | husky v9 (2024) | `add` subcommand removed; init creates scaffold |
| `husky install` in prepare script | `"prepare": "husky"` (no `install` subarg) | husky v9 | Simplified CLI |
| `@typescript-eslint/eslint-plugin` + `@typescript-eslint/parser` separately | `typescript-eslint` (unified package) | typescript-eslint v6+ | Single package import replaces two packages |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | ESLint, husky install | ✓ | (frontend/node_modules present) | — |
| ESLint | D-01/D-04 | ✓ | 9.39.2 (in node_modules) | — |
| typescript-eslint | D-02 | ✓ | 8.53.1 (in node_modules) | — |
| eslint-plugin-react-hooks | D-02 | ✓ | 7.0.1 (in node_modules) | — |
| eslint-plugin-react-refresh | D-02 | ✓ | 0.4.26 (in node_modules) | — |
| @eslint/js | D-02 | ✓ | 9.39.2 (in node_modules) | — |
| globals | D-02 | ✓ | 16.5.0 (in node_modules) | — |
| husky | D-08/D-12 | ✗ | — | None (must install) |
| lint-staged | D-08/D-09/D-10 | ✗ | — | None (must install) |
| ruff | D-13 | ✓ | available via `python -m ruff` | — |

**Missing dependencies with no fallback:**
- `husky@9.1.7` — not in node_modules; install via `npm install --save-dev husky`
- `lint-staged@16.4.0` — not in node_modules; install via `npm install --save-dev lint-staged`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend); no frontend test framework configured |
| Config file | `backend/pyproject.toml` (ruff config only; pytest uses defaults) |
| Quick run command | `pytest -m "not integration" --tb=short -q` (from `backend/`) |
| Full suite command | `pytest --tb=short -q` (from `backend/`) |

### Phase Requirements → Test Map

Phase 16 has no explicit REQ-XX requirement IDs (TBD per phase definition). The verifiable behaviors are:

| Behavior | Test Type | Automated Command | Notes |
|----------|-----------|-------------------|-------|
| `npm run lint` exits 0 | smoke | `cd frontend && npm run lint` | Creates ESLint config; validates D-04 |
| ruff reports 0 violations | smoke | `python -m ruff check backend/` | Validates D-13 |
| husky pre-commit hook exists | manual | Check `.husky/pre-commit` file exists | File existence check |
| CI ESLint step present in deploy-test.yml | manual | Read workflow file | Text inspection |
| `npm install` triggers `prepare` (husky init) | smoke | `cd frontend && npm install` then check `.husky/` | Validates D-11 |

### Sampling Rate

- **Per task commit:** `cd frontend && npm run lint` and `python -m ruff check backend/`
- **Per wave merge:** Same (all changes are in the linting tooling itself)
- **Phase gate:** Both linters clean + CI step confirmed before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `frontend/eslint.config.js` — must be created (Wave 0 / task 1); no test file needed, the linter itself is the artifact
- [ ] `.husky/pre-commit` — must be created after husky install
- [ ] `husky` and `lint-staged` — must be installed before pre-commit scaffold exists

*(No new pytest test files required for this phase — the linting tools themselves are the deliverables, validated by running them.)*

---

## Open Questions

1. **lint-staged Python glob scope**
   - What we know: lint-staged config lives in `frontend/package.json`; ruff is invoked from that directory
   - What's unclear: Whether `**/*.py` will correctly find staged Python files in `backend/` relative to the repo root, or whether an explicit `../backend/**/*.py` pattern is needed
   - Recommendation: Test with `**/*.py` first (lint-staged resolves globs against repo root when run from within a git repo); if it matches unwanted files, narrow to `backend/**/*.py`

2. **npm ci duplication in CI**
   - What we know: The `npm audit` step already runs `npm ci`; the new ESLint step also runs `npm ci` per D-07
   - What's unclear: Whether running `npm ci` twice in the same job has meaningful performance cost
   - Recommendation: Accept the duplication for self-containment (it's idempotent and the CI layer caches node_modules via actions/cache if desired later); no action needed now

---

## Sources

### Primary (HIGH confidence)

- ESLint v9 flat config docs (eslint.org/docs/latest/use/configure/configuration-files) — flat config format, `ignores` object
- typescript-eslint v8 docs (typescript-eslint.io/getting-started) — `tseslint.config()` helper pattern
- Direct inspection: `frontend/node_modules/eslint/package.json` — version 9.39.2 confirmed
- Direct inspection: `frontend/node_modules/typescript-eslint/package.json` — version 8.53.1 confirmed
- Direct run: `cd frontend && npm run lint` — confirmed crash message (missing eslint.config.js)
- Direct run: `python -m ruff check backend/` — confirmed exactly 1 violation (F401 in test_tagging_allocation.py:7)
- Direct run: `npm view husky version` — 9.1.7; `npm view lint-staged version` — 16.4.0

### Secondary (MEDIUM confidence)

- husky v9 migration guide (typicode.github.io/husky/get-started) — `prepare` script syntax, CI env skip behavior, `husky init` replacing `husky add`
- lint-staged README (github.com/lint-staged/lint-staged) — glob matching behavior, `package.json` config placement

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages directly verified in node_modules; versions confirmed
- Architecture: HIGH — eslint.config.js pattern is the official Vite scaffold for ESLint v9; no inference required
- Pitfalls: HIGH (P1-P2 from official docs), MEDIUM (P3 lint-staged glob behavior; verified by docs not live test), HIGH (P4-P5 from husky v9 changelog)

**Research date:** 2026-03-25
**Valid until:** 2026-06-25 (stable tooling; ESLint/husky version bumps unlikely to break these patterns within 90 days)
