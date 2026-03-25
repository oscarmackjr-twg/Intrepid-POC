# Phase 16: Linting - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish working, enforced linting across the full project:
- **Frontend:** Create `eslint.config.js` so `npm run lint` works (currently crashes with config-not-found)
- **Backend:** Fix the 1 existing ruff violation (unused import); no rule expansion
- **CI:** Wire ESLint into `deploy-test.yml` as a blocking step alongside ruff
- **Pre-commit:** Add husky + lint-staged so violations are caught before commit

Does NOT include: adding type-checking rules, expanding ruff rule sets, mypy config changes, or frontend formatting (Prettier).

</domain>

<decisions>
## Implementation Decisions

### ESLint config (frontend)
- **D-01:** Create `frontend/eslint.config.js` with minimal ruleset only — react-hooks + react-refresh plugins
- **D-02:** Use the packages already installed: `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals`
- **D-03:** No TypeScript strict rules — keep zero new violations at the point of setup
- **D-04:** Config must make `npm run lint` (which runs `eslint .`) pass cleanly

### CI gate (frontend lint in deploy-test.yml)
- **D-05:** Add `npm run lint` as a blocking step in `.github/workflows/deploy-test.yml`
- **D-06:** The step runs inside the frontend directory (`working-directory: frontend`)
- **D-07:** Runs `npm ci` before linting (install deps first)

### Pre-commit hooks (husky + lint-staged)
- **D-08:** Add `husky` and `lint-staged` to frontend devDependencies
- **D-09:** lint-staged config: run `eslint --fix` on staged `*.ts` and `*.tsx` files
- **D-10:** lint-staged config: run `ruff check --fix` on staged `*.py` files (from backend/)
- **D-11:** `prepare` script in `frontend/package.json` to install husky hooks on `npm install`
- **D-12:** Pre-commit hook file at `.husky/pre-commit` running `npx lint-staged`

### Backend ruff
- **D-13:** Fix the 1 existing ruff violation (unused import) — use `ruff check --fix backend/`
- **D-14:** No changes to `backend/pyproject.toml` ruff config (existing config is correct)

### Claude's Discretion
- Exact `eslint.config.js` syntax (flat config format required for ESLint v9)
- Which files/directories to ignore in ESLint config (node_modules, dist)
- Whether to place `lint-staged` config in `package.json` or `.lintstagedrc`

</decisions>

<specifics>
## Specific Ideas

- The ESLint config must use flat config format (`eslint.config.js` exports an array) — ESLint v9 dropped the old `.eslintrc` format
- husky + lint-staged is the standard pairing for this; no custom git hooks
- ruff lint-staged scope should be `backend/**/*.py` (not all .py files in the repo root)

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing lint configuration
- `backend/pyproject.toml` — Ruff config: line-length=120, ignored rules (E712, E402), excluded scripts

### CI workflow
- `.github/workflows/deploy-test.yml` — Current CI pipeline; add ESLint step here alongside existing ruff/mypy steps

### Frontend package setup
- `frontend/package.json` — Current scripts, devDependencies (eslint v9 and plugins already installed)

No external specs — requirements are fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/package.json` devDependencies already include: `eslint@^9.39.1`, `@eslint/js`, `typescript-eslint@^8.46.4`, `eslint-plugin-react-hooks@^7.0.1`, `eslint-plugin-react-refresh@^0.4.24`, `globals` — no new packages needed for ESLint config itself

### Established Patterns
- Backend CI pattern (in deploy-test.yml): `pip install ruff mypy` → `ruff check backend/` → `ruff format --check backend/` → `mypy backend/ ...`
- Frontend CI should follow same pattern: `npm ci` → `npm run lint`

### Integration Points
- `deploy-test.yml` security-quality-gate job already exists (from Phase 7/12) — ESLint step goes into this job
- `frontend/package.json` `scripts` block gets a `prepare` entry for husky

</code_context>

<deferred>
## Deferred Ideas

- Prettier / auto-formatting for frontend — not in scope
- TypeScript strict ESLint rules (typescript-eslint/recommended-type-checked) — not in scope, would require tsconfig setup
- Expanding ruff rules (isort, bugbear, naming) — explicitly deferred
- mypy config tightening — not in scope

</deferred>

---

*Phase: 16-linting*
*Context gathered: 2026-03-25*
