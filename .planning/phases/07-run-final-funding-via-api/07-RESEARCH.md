# Phase 7: Application Hardening - Research

**Researched:** 2026-03-10
**Domain:** Security hardening — AWS networking, secrets management, auth token storage, error leakage, CI quality gates, audit logging, repository hygiene
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**1. AWS Networking / TLS**
- RDS must move to private subnets — remove `publicly_accessible = true` from `deploy/terraform/qa/rds.tf`
- ALB HTTPS: add TLS listener with ACM cert ARN as a Terraform variable (leave cert ARN to be filled in — not blocking the PR)
- Add HTTP → HTTPS redirect (port 80 → 443) in ALB listener rules
- Tighten security group egress: replace default `0.0.0.0/0` open egress in `deploy/terraform/qa/security-groups.tf:31` with minimal required rules

**2. Default Secrets / Bootstrap Passwords**
- App must fail startup (outside explicit local-dev mode) when `SECRET_KEY` is the hardcoded fallback (`backend/config/settings.py:52`)
- Remove default `admin123` password and other known analyst default passwords from `backend/scripts/seed_admin.py` and `README.md`
- Seed/reset scripts should generate a one-time random password and print it once — never a fixed known value
- Password policy at registration and reset: minimum 12 characters, at least one uppercase, one lowercase, one digit

**3. Frontend Auth (localStorage replacement)**
- Replace `localStorage` token handling in `frontend/src/contexts/AuthContext.tsx` with HttpOnly/Secure/SameSite=Strict cookies
- Backend login endpoint sets the cookie; frontend never stores the token in JS-accessible storage
- Add CSP header to backend responses
- Add rate limiting and failed-login monitoring to `backend/auth/routes.py` login endpoint

**4. File / Error Endpoint Leakage**
- Never return `file://` URIs to clients — remove from `backend/api/files.py` and `backend/storage/local.py`
- Replace all `str(e)` / raw exception text in HTTP responses with generic client-facing messages plus a server-side correlation ID in logs
- Affects: `backend/api/files.py:44`, `backend/api/files.py:97`, `backend/api/files.py:165`
- All file area endpoints must require authenticated user — no anonymous access

**5. CI Security / Quality Gates**
- Add a required CI job that runs before deploy in `deploy-test.yml`
- Tools: ruff (Python lint/format), mypy (type checks), pip-audit (Python dependency CVEs), npm audit (frontend), Terraform validate
- Job must be blocking — deploy cannot proceed if any gate fails

**6. Durable Audit Logging**
- Persist security-relevant events to a new `audit_log` Postgres table (not just application log output)
- Current `backend/auth/audit.py` only writes to the logger — upgrade to DB persistence
- Events: login success/failure, file access, run start/cancel, admin actions, auth failures
- Table schema: event_type, user_id, timestamp, source_ip, resource, outcome, detail_json
- Use `TIMESTAMPTZ` for timestamp, `JSONB` for detail_json

**7. Repository Hygiene**
- Remove `loan-engine-qa.pem` from workspace and ensure gitignored
- Remove `deploy/aws/eb/app-bundle.zip` from source control (IS currently tracked — needs `git rm`)
- Confirm sample datasets are sanitized (no real PII)
- Enable secret scanning in GitHub CI

### Claude's Discretion
- Specific ruff rule set and mypy strictness level — use sensible defaults for an existing codebase (not maximally strict)
- Correlation ID implementation detail (UUID header vs structured log field)
- Exact SG egress rules (allow only what ECS tasks need: RDS port, S3 endpoint, SES, ECR)
- CSP header specifics (allow same-origin, deny inline scripts except Vite dev build)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HARD-01 | AWS networking/TLS: RDS to private subnets, ALB HTTPS, SG egress tightening | Terraform `aws_db_subnet_group` subnet_ids change; `aws_lb_listener` HTTPS + redirect; `aws_vpc_security_group_egress_rule` replacement |
| HARD-02 | Default secrets/bootstrap passwords: startup guard, remove hardcoded passwords, password policy | `pydantic_settings` model_validator pattern already in settings.py; `secrets.token_urlsafe(16)` for one-time password; regex validator on UserCreate.password |
| HARD-03 | Frontend auth token storage: localStorage → HttpOnly cookies | FastAPI `Response.set_cookie`; Axios `withCredentials: true`; `get_current_user` cookie fallback |
| HARD-04 | File/error endpoint leakage: no file:// URIs, sanitized error responses, correlation IDs | `local.py:103` returns `file://` — replace with relative path or `/api/files/download/` link; `uuid.uuid4()` correlation ID in request context |
| HARD-05 | CI security/quality gates: ruff, mypy, pip-audit, npm audit, terraform validate | New `security-quality-gate` job in `deploy-test.yml`; `needs: security-quality-gate` on deploy job |
| HARD-06 | Durable audit logging: audit_log Postgres table, DB persistence | New Alembic migration; `JSONB` + `TIMESTAMPTZ` columns; psycopg2 `INET` for source_ip; update `backend/auth/audit.py` functions to write to DB |
| HARD-07 | Repository hygiene: remove tracked secrets/bundles, gitignore, secret scanning | `git rm --cached deploy/aws/eb/app-bundle.zip`; PEM file already untracked (gitignored); GitHub secret scanning via `truffleHog` or native GitHub feature |
</phase_requirements>

---

## Summary

Phase 7 is a pure hardening phase with no new product features. The seven areas span three distinct layers: AWS infrastructure (Terraform changes), backend application code (Python/FastAPI), and CI pipeline (GitHub Actions YAML). Each area has well-understood patterns. Most changes are small, surgical edits to existing files rather than net-new subsystems.

The highest-complexity item is the frontend auth token migration (HARD-03). Replacing `localStorage` with HttpOnly cookies requires coordinated changes in the FastAPI login endpoint, the `get_current_user` dependency, the Axios interceptor, and all references to `localStorage` in `AuthContext.tsx`. The SPA-and-cookie interaction with CORS requires attention: `axios.defaults.withCredentials = true` and FastAPI `CORSMiddleware` must explicitly list origins (not wildcard) and set `allow_credentials=True`.

The second complexity spike is the audit log DB table (HARD-06). The `final_funding_job` table in `program_run_jobs.py` uses raw psycopg2 `CREATE TABLE IF NOT EXISTS` with `TIMESTAMPTZ` and `JSONB`. The `audit_log` table should follow the same pattern AND go through Alembic (unlike `final_funding_job`). The existing migration is in `backend/migrations/versions/` with one file (`60a8a67090c8_initial_schema.py`). A new migration file is needed.

**Primary recommendation:** Implement as seven sequential tasks, one per HARD requirement. Each task is self-contained and independently verifiable. Order: HARD-07 (repo hygiene, zero risk) → HARD-01 (Terraform, infrastructure only) → HARD-02 (secrets/passwords) → HARD-04 (error leakage) → HARD-06 (audit log) → HARD-03 (auth cookies, most fragile) → HARD-05 (CI gates last, validates all prior changes).

---

## Standard Stack

### Core (already in requirements.txt)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.109.0 | HTTP framework; `Response.set_cookie`, `CORSMiddleware` | Already in use |
| passlib[bcrypt] | 1.7.4 | Password hashing | Already in use |
| pydantic-settings | 2.5.2 | Settings with validators | Already in use; `model_validator` pattern used |
| alembic | 1.14.0 | DB migrations | Already in use; `backend/migrations/` |
| sqlalchemy | 2.0.36 | ORM | Already in use |
| python-jose | 3.3.0 | JWT | Already in use |

### New Dependencies Needed
| Library | Version | Purpose | Install |
|---------|---------|---------|---------|
| slowapi | >=0.1.9 | Rate limiting for FastAPI login endpoint | `pip install slowapi` |
| ruff | >=0.4.0 | Python linting + formatting in CI | CI-only, `pip install ruff` |
| mypy | >=1.10.0 | Static type checking in CI | CI-only, `pip install mypy` |
| pip-audit | >=2.7.0 | Python CVE scanning in CI | CI-only, `pip install pip-audit` |

### CI-Only (GitHub Actions, no requirements.txt change needed)
| Tool | Version | Purpose |
|------|---------|---------|
| ruff | latest | Python lint — `ruff check backend/ && ruff format --check backend/` |
| mypy | latest | Type check — `mypy backend/ --ignore-missing-imports --no-strict-optional` |
| pip-audit | latest | CVE scan — `pip-audit -r backend/requirements.txt` |
| npm audit | built-in npm | JS CVE scan — `npm audit --audit-level=high` |
| terraform validate | terraform CLI | Terraform syntax — `terraform validate` |

### Installation (new runtime dep only)
```bash
# In backend/requirements.txt — add:
slowapi>=0.1.9
```

---

## Architecture Patterns

### Recommended File Change Map
```
backend/
├── config/settings.py         # Add startup SECRET_KEY guard (model_validator)
├── auth/
│   ├── routes.py              # Rate limiting (slowapi), cookie-set on login, password policy
│   ├── security.py            # get_current_user: add cookie fallback/replacement
│   └── audit.py               # Add DB write alongside logger.info
├── api/
│   └── files.py               # Sanitize str(e) responses, remove file:// URL responses
├── storage/
│   └── local.py               # Replace file:// URL with relative path or None
├── db/
│   └── models.py              # Add AuditLog SQLAlchemy model
└── migrations/versions/
    └── XXXX_add_audit_log.py  # New Alembic migration

deploy/
├── terraform/qa/
│   ├── rds.tf                 # publicly_accessible = false; subnet_ids = private
│   ├── alb.tf                 # Add HTTPS listener, redirect rule on port 80
│   ├── security-groups.tf     # Tighten ecs_all egress, rds_all egress
│   └── variables.tf           # Add acm_certificate_arn variable

.github/workflows/
└── deploy-test.yml            # Add security-quality-gate job; deploy needs: [security-quality-gate]
```

### Pattern 1: FastAPI HttpOnly Cookie Auth (HARD-03)

The key insight: FastAPI's `OAuth2PasswordBearer` dependency reads from the `Authorization` header only. To accept cookies, `get_current_user` must be replaced with a custom dependency that checks cookies first, falls back to the header.

**Login endpoint change:**
```python
# Source: FastAPI docs — https://fastapi.tiangolo.com/tutorial/response-model/
from fastapi import Response

@router.post("/login")
async def login(response: Response, form_data: ..., db: ...):
    # ... existing auth logic ...
    access_token = create_access_token(...)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,          # only sent over HTTPS
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    # Return user info only — no token in JSON body
    return {"user": {...}}
```

**get_current_user cookie + header fallback:**
```python
from fastapi import Request, Cookie
from typing import Optional

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    cookie_token: Optional[str] = Cookie(default=None, alias="access_token"),
) -> User:
    token = None
    auth_header = request.headers.get("Authorization")
    if cookie_token and cookie_token.startswith("Bearer "):
        token = cookie_token[len("Bearer "):]
    elif auth_header and auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
    if not token:
        raise HTTPException(status_code=401, ...)
    # ... existing JWT decode logic ...
```

**Frontend AuthContext.tsx change:**
- Remove all `localStorage.setItem/getItem/removeItem('token')` calls (lines 34, 70, 85, 107, 114)
- Remove `axios.defaults.headers.common['Authorization']` setter calls
- Add `axios.defaults.withCredentials = true` once at module level
- `login()` simply calls the endpoint; the cookie is set automatically by the browser
- `fetchUser()` on mount calls `/api/auth/me` with credentials; 401 means not logged in
- `logout()` calls a new `POST /api/auth/logout` that clears the cookie server-side

**CORS must allow credentials when using cookies:**
```python
# backend/main.py or wherever CORSMiddleware is configured
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Must be explicit list, NOT ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Pattern 2: Rate Limiting with slowapi (HARD-03)

```python
# Source: slowapi docs — https://slowapi.readthedocs.io/
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, ...):
    ...
```

### Pattern 3: Correlation ID in Error Responses (HARD-04)

Use a UUID generated per-exception, logged server-side, returned as an opaque reference to the client.

```python
import uuid

@router.get("/list")
async def list_files(...):
    try:
        ...
    except Exception as e:
        correlation_id = str(uuid.uuid4())
        logger.error("Error listing files [correlation_id=%s]: %s", correlation_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An internal error occurred (ref: {correlation_id})"
        )
```

The client sees a safe message with a reference. Ops can grep logs for the correlation_id.

### Pattern 4: SECRET_KEY Startup Guard (HARD-02)

The existing `settings.py` uses `pydantic_settings` `model_validator`. A second validator runs at startup and raises `ValueError` if SECRET_KEY is the known fallback.

```python
# backend/config/settings.py — add after existing validators
KNOWN_FALLBACK_SECRET = "your-secret-key-change-in-production"
LOCAL_DEV_MODE: bool = False  # Set True in .env for local dev to skip this check

@model_validator(mode="after")
def validate_secret_key(self) -> "Settings":
    if not self.LOCAL_DEV_MODE and self.SECRET_KEY == self.KNOWN_FALLBACK_SECRET:
        raise ValueError(
            "SECRET_KEY is set to the default fallback value. "
            "Set a strong random SECRET_KEY in environment or Secrets Manager, "
            "or set LOCAL_DEV_MODE=true in .env for local development."
        )
    return self
```

`LOCAL_DEV_MODE=true` is added to `backend/.env` and `.env.example` — never to production.

### Pattern 5: Password Policy Validator (HARD-02)

Pydantic v2 field validator on the `UserCreate` and `UserUpdate` password field.

```python
from pydantic import field_validator
import re

class UserCreate(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v
```

### Pattern 6: Audit Log Table + DB Write (HARD-06)

The `final_funding_job` table established the JSONB + TIMESTAMPTZ pattern. The `audit_log` table goes through Alembic, following `60a8a67090c8_initial_schema.py` structure.

**SQLAlchemy model (backend/db/models.py):**
```python
from sqlalchemy.dialects.postgresql import JSONB, INET

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    source_ip = Column(String(45), nullable=True)   # IPv4 or IPv6 string
    resource = Column(String(500), nullable=True)
    outcome = Column(String(20), nullable=True)      # "success" | "failure"
    detail_json = Column(JSON, nullable=True)         # Use JSON not JSONB for SQLite compat in tests
```

**Important**: Use `sqlalchemy.JSON` (not `JSONB`) in the model so SQLite test fixtures work. The migration can use `postgresql.JSONB` explicitly:
```python
# In Alembic migration:
from sqlalchemy.dialects import postgresql
op.add_column('audit_log', sa.Column('detail_json', postgresql.JSONB(), nullable=True))
```

**Alembic migration command:**
```bash
cd backend
alembic revision --autogenerate -m "add_audit_log_table"
# Review generated file then:
alembic upgrade head
```

**Updated audit.py write pattern:**
```python
def log_user_action(action, user, db: Session, source_ip=None, resource=None, outcome="success", details=None):
    # 1. Always write to logger (existing behavior)
    logger.info("User action: %s", {...})
    # 2. Also write to DB
    entry = AuditLog(
        event_type=action,
        user_id=user.id if user else None,
        source_ip=source_ip,
        resource=resource,
        outcome=outcome,
        detail_json=details or {},
    )
    db.add(entry)
    db.commit()
```

**Callers must pass `db` and `request`:** The login route already has `db: Session`. Extract `source_ip` from `request.client.host`.

### Pattern 7: Terraform — Private Subnets + ALB HTTPS (HARD-01)

**rds.tf changes:**
```hcl
# Change: subnet_ids to private subnets
resource "aws_db_subnet_group" "main" {
  subnet_ids = aws_subnet.private[*].id   # was: aws_subnet.public[*].id
  ...
}

resource "aws_db_instance" "main" {
  publicly_accessible = false             # was: true
  ...
}
```

**Prerequisite check**: The VPC must have private subnets. Verify `network.tf` defines `aws_subnet.private` resources. If private subnets don't exist yet, they must be created in the same Terraform apply.

**alb.tf HTTPS listener addition:**
```hcl
# variables.tf addition:
variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS. Leave empty string to skip HTTPS (dev/QA without cert)."
  type        = string
  default     = ""
}

# alb.tf — change existing HTTP listener to redirect:
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# alb.tf — new HTTPS listener:
resource "aws_lb_listener" "https" {
  count             = var.acm_certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
```

**security-groups.tf egress tightening:**

Replace `ecs_all` and `rds_all` open egress with specific rules:
```hcl
# ECS egress: RDS (5432), HTTPS for S3/ECR/SES (443), DNS (53)
resource "aws_vpc_security_group_egress_rule" "ecs_rds" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.rds.id
  from_port    = 5432
  to_port      = 5432
  ip_protocol  = "tcp"
}
resource "aws_vpc_security_group_egress_rule" "ecs_https" {
  security_group_id = aws_security_group.ecs.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}
resource "aws_vpc_security_group_egress_rule" "ecs_dns" {
  security_group_id = aws_security_group.ecs.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 53
  to_port           = 53
  ip_protocol       = "udp"
}

# RDS: no egress needed (Postgres does not initiate outbound connections)
# Remove rds_all; add nothing (or keep with restrictive no-rule approach)
```

**ALB egress**: The ALB does need open egress to forward to ECS tasks on port 8000. Keep `alb_all` or replace with `alb_to_ecs`.

### Pattern 8: CI Security Gate Job (HARD-05)

```yaml
# .github/workflows/deploy-test.yml — insert before deploy job
jobs:
  security-quality-gate:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install CI tools
        run: pip install ruff mypy pip-audit

      - name: Ruff lint
        run: ruff check backend/

      - name: Ruff format check
        run: ruff format --check backend/

      - name: Mypy type check
        run: mypy backend/ --ignore-missing-imports --no-strict-optional --exclude venv

      - name: pip-audit CVE scan
        run: pip-audit -r backend/requirements.txt

      - name: npm audit
        working-directory: frontend
        run: |
          npm ci
          npm audit --audit-level=high

      - name: Terraform validate
        working-directory: deploy/terraform/qa
        run: |
          terraform init -backend=false
          terraform validate

  deploy:
    needs: [security-quality-gate]   # Blocking dependency
    ...
```

### Pattern 9: One-Time Seed Password (HARD-02)

```python
# backend/scripts/seed_admin.py — replace hardcoded defaults
import secrets

def create_admin_user(...):
    one_time_password = secrets.token_urlsafe(16)
    # Use one_time_password instead of "admin123"
    print(f"Generated one-time password: {one_time_password}")
    print("IMPORTANT: Save this password now — it will not be shown again.")
```

The `additional_users` block with `default_password = "twg123"` must also be removed. Each additional user should either be seeded with individual one-time passwords or removed from the automated seed entirely.

### Pattern 10: file:// URL Removal (HARD-04)

`backend/storage/local.py:103` generates `file://{file_path.as_uri()}`. The `/api/files/url/{file_path}` endpoint calls `storage.get_file_url()` and returns this to the client.

**Fix**: Return a relative API download path instead:
```python
def get_file_url(self, path: str, expires_in: int = 3600) -> str:
    """For local storage, return a relative API path. Client uses /api/files/download/."""
    file_path = self._resolve_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    # Return API path, not filesystem path
    return f"/api/files/download/{path}"
```

### Anti-Patterns to Avoid

- **`allow_origins=["*"]` with `allow_credentials=True`**: FastAPI raises a RuntimeError. Must be explicit origin list.
- **Setting cookie `secure=True` on localhost**: Breaks local dev — either skip `secure` when `LOCAL_DEV_MODE=True` or accept that cookie auth requires HTTPS in staging (which it will have after HARD-01).
- **Removing `Authorization` header support entirely**: Some clients (ECS one-off task scripts, Alembic migration tool testing) use Bearer token. Keep the header fallback in `get_current_user`.
- **Alembic autogenerate with JSONB**: Alembic detects `JSON` in the model but may not generate `JSONB` for Postgres. The migration file should be reviewed and the column type manually set to `postgresql.JSONB` if needed.
- **`terraform apply` without plan on `publicly_accessible = false`**: Changing this on an existing RDS instance forces a modify (not destroy/recreate) but requires a brief maintenance window. This is expected behavior and should be noted in the plan.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting | Custom in-memory counter | `slowapi` | Thread safety, Redis backend option, standard decorator API |
| Password strength validation | Custom regex function | Pydantic `field_validator` | Integrated with FastAPI request validation, consistent 422 responses |
| Dependency CVE scanning | Manual pip-audit scripting | `pip-audit` CLI | Maintained by PyPA, PURL-based, integrates with GitHub OIDC |
| JWT in cookies | Custom cookie parsing | FastAPI `Cookie()` dependency | Standard dependency injection, handles missing values gracefully |
| Terraform HTTPS | Manual ACM association | `aws_lb_listener` with `certificate_arn` | AWS-native, handles TLS termination at ALB |

---

## Common Pitfalls

### Pitfall 1: CORS + Cookies in SPA
**What goes wrong:** Setting `withCredentials: true` on Axios but `allow_origins=["*"]` in FastAPI CORS config causes all credentialed requests to fail with CORS error.
**Why it happens:** The CORS spec forbids wildcard origins with credentialed requests.
**How to avoid:** Ensure `settings.CORS_ORIGINS` contains explicit origins (it does: `["http://localhost:5173", "http://localhost:3000"]`) and `allow_credentials=True` is set in `CORSMiddleware`.
**Warning signs:** Browser console shows `CORS error: The value of 'Access-Control-Allow-Origin' header must not be wildcard '*'`.

### Pitfall 2: Cookie `secure` Flag in Local Dev
**What goes wrong:** `secure=True` on the cookie means it is only sent over HTTPS. Local dev runs on HTTP (`localhost:5173` → `localhost:8000`). The browser silently drops the cookie, authentication breaks in local dev.
**How to avoid:** Gate `secure=True` on `not settings.LOCAL_DEV_MODE`. When `LOCAL_DEV_MODE=True`, set `secure=False`.
**Warning signs:** Login appears to succeed (200 from server) but subsequent requests return 401.

### Pitfall 3: RDS publicly_accessible + Private Subnet Conflict
**What goes wrong:** Setting `publicly_accessible = false` while the `aws_db_subnet_group` still points at public subnets. Postgres becomes unreachable from ECS (ECS can't route to public subnets in this VPC config).
**How to avoid:** Both changes must happen together in the same Terraform apply: `publicly_accessible = false` AND `subnet_ids = aws_subnet.private[*].id`.
**Warning signs:** ECS tasks start failing with DB connection errors after `terraform apply`.
**Check first:** Verify private subnets exist in `deploy/terraform/qa/network.tf` before planning this change.

### Pitfall 4: Audit Log `db` Session in Background Tasks
**What goes wrong:** Final funding jobs run in background threads (`threading.Thread`) that don't have a FastAPI request context. Passing a SQLAlchemy `Session` to a background thread that was created in the request context causes `DetachedInstanceError` or database connection pool exhaustion.
**How to avoid:** Background tasks should create their own `SessionLocal()` and close it when done. The audit log writes inside request handlers (login, file access) are safe; do not attempt to audit log from the FF job background thread using the request's session.

### Pitfall 5: Alembic Migration with SQLite in Tests
**What goes wrong:** Adding `JSONB` or `TIMESTAMPTZ` column types to the SQLAlchemy model causes test failures because SQLite (used in `conftest.py`) doesn't understand those types.
**Why it happens:** `conftest.py` uses `sqlite:///:memory:` and calls `Base.metadata.create_all()` which processes the model's column types.
**How to avoid:** Use `sa.JSON` in the model (cross-DB compatible); use `postgresql.JSONB` only in the Alembic migration file (runs against real Postgres). For `TIMESTAMPTZ`, use `sa.DateTime(timezone=True)` in the model — SQLite accepts this, Postgres maps it to TIMESTAMPTZ.

### Pitfall 6: `git rm` on app-bundle.zip
**What goes wrong:** Simply adding `*.zip` to `.gitignore` does not remove already-tracked files from git history.
**How to avoid:** `git rm --cached deploy/aws/eb/app-bundle.zip` removes it from the index without deleting the file from disk. Commit the removal. Then add `deploy/aws/eb/*.zip` to `.gitignore`.

### Pitfall 7: mypy on Existing Codebase
**What goes wrong:** Running `mypy` with strict mode on an existing codebase that has no type annotations generates hundreds of errors, making the CI gate un-mergeable.
**How to avoid:** Use `--ignore-missing-imports --no-strict-optional`. Add `# type: ignore` sparingly for known-noisy callsites (pandas, dynamic SQLAlchemy). Do not use `--strict`.

---

## Code Examples

### Verified: FastAPI `Response.set_cookie` signature
```python
# Source: FastAPI docs (https://fastapi.tiangolo.com/advanced/response-cookies/)
from fastapi import Response

@app.get("/set-cookie")
def set_cookie(response: Response):
    response.set_cookie(
        key="fakesession",
        value="fake-cookie-session-value",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=1800,
    )
    return {"message": "Come to the dark side, we have cookies"}
```

### Verified: FastAPI read cookie in dependency
```python
# Source: FastAPI docs (https://fastapi.tiangolo.com/tutorial/cookie-params/)
from fastapi import Cookie
from typing import Optional

async def some_endpoint(access_token: Optional[str] = Cookie(default=None)):
    ...
```

### Verified: Alembic migration file structure
```python
# Source: backend/migrations/versions/60a8a67090c8_initial_schema.py (existing pattern)
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'XXXX'
down_revision = '60a8a67090c8'

def upgrade() -> None:
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_ip', sa.String(length=45), nullable=True),
        sa.Column('resource', sa.String(length=500), nullable=True),
        sa.Column('outcome', sa.String(length=20), nullable=True),
        sa.Column('detail_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_log_event_type', 'audit_log', ['event_type'])
    op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])

def downgrade() -> None:
    op.drop_table('audit_log')
```

### Verified: secrets module for one-time password
```python
# Source: Python stdlib docs (https://docs.python.org/3/library/secrets.html)
import secrets
password = secrets.token_urlsafe(16)  # 22-char URL-safe base64 string
```

### Verified: slowapi rate limiting pattern
```python
# Source: slowapi docs (https://slowapi.readthedocs.io/en/latest/)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)
# In app setup:
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# On route:
@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, ...):
    ...
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `localStorage` JWT storage | HttpOnly cookie | Eliminates XSS token theft |
| Logger-only audit trail | DB-persisted audit_log | Survives container restarts, queryable |
| Open egress SG rules | Minimal required egress | Defense-in-depth; limits blast radius if ECS task compromised |
| Hardcoded fallback SECRET_KEY | Startup guard + LOCAL_DEV_MODE escape hatch | Prevents accidental production misconfiguration |
| HTTP-only ALB | HTTPS with HTTP→301 redirect | Encrypts traffic in transit |

**Deprecated/outdated in this codebase:**
- `deploy/aws/eb/` Elastic Beanstalk artifacts: project moved to ECS/Fargate. The EB bundle is vestigial and tracked in git.
- `backend/storage/local.py` `get_file_url` returning `file://`: was probably fine for local exploration, now incorrect for any networked use.

---

## Key Facts About Existing Code

These are precise observations that the planner must know to write correct tasks:

### Repository Hygiene (HARD-07)
- `loan-engine-qa.pem` is in the root `.gitignore` (line 3) and is **NOT tracked in git** — no `git rm` needed. Just verify it stays gitignored.
- `deploy/aws/eb/app-bundle.zip` **IS tracked in git** (confirmed via `git ls-files`) — requires `git rm --cached`.
- `.gitignore` already lists `loan-engine-qa.pem` — no new entry needed.
- The PEM file exists on disk at the repo root.

### Terraform (HARD-01)
- `deploy/terraform/qa/rds.tf:29` — `publicly_accessible = true` — the only change needed here
- `deploy/terraform/qa/rds.tf:6` — `subnet_ids = aws_subnet.public[*].id` — change to `aws_subnet.private[*].id`
- `deploy/terraform/qa/alb.tf:36-45` — single HTTP listener currently, no HTTPS listener exists
- `deploy/terraform/qa/security-groups.tf:31` — `ecs_all` egress is `0.0.0.0/0 -1 (all traffic)` — the open egress
- `deploy/terraform/qa/security-groups.tf:85` — `rds_all` egress is also `0.0.0.0/0 -1` — also open

### Settings (HARD-02)
- `backend/config/settings.py:52` — `SECRET_KEY: str = "your-secret-key-change-in-production"` — this exact string is the sentinel value to check

### Seed Script (HARD-02)
- `backend/scripts/seed_admin.py:27` — `password: str = "admin123"` — default argument
- `backend/scripts/seed_admin.py:181` — `default_password = "twg123"` — hardcoded for analyst users (nparakh, jbalaji, gdehankar, hkhandelwal)
- Both must be replaced with `secrets.token_urlsafe(16)` per-user generation

### Auth Context (HARD-03)
- `frontend/src/contexts/AuthContext.tsx:34` — `localStorage.getItem('token')` in Axios interceptor
- `frontend/src/contexts/AuthContext.tsx:51` — `localStorage.removeItem('token')` in 401 interceptor
- `frontend/src/contexts/AuthContext.tsx:70` — `localStorage.getItem('token')` in `useEffect`
- `frontend/src/contexts/AuthContext.tsx:85` — `localStorage.removeItem('token')` in `fetchUser` catch
- `frontend/src/contexts/AuthContext.tsx:107` — `localStorage.setItem('token', access_token)` in `login()`
- `frontend/src/contexts/AuthContext.tsx:114` — `localStorage.removeItem('token')` in `logout()`

### Files API (HARD-04)
- `backend/api/files.py:44` — `detail=f"Failed to list files: {str(e)}"` — leaks internal error
- `backend/api/files.py:97` — `detail=f"Failed to upload file: {detail}"` where `detail = str(e)` — leaks internal error
- `backend/api/files.py:165` — `detail=f"Failed to get file URL: {str(e)}"` — leaks internal error
- `backend/storage/local.py:103` — `return f"file://{file_path.as_uri()}"` — leaks filesystem path

### Test Infrastructure (HARD-06, HARD-03, HARD-02)
- Framework: `pytest` 8.3.3
- Config: `backend/pytest.ini` — `testpaths = tests`, `-m "not integration"` by default
- Session DB: `sqlite:///:memory:` via `conftest.py:test_db_engine` (session scope)
- Quick run: `cd backend && pytest tests/ -x -q`
- Full suite: `cd backend && pytest tests/`
- Existing test files: `test_auth_routes.py` and `test_auth_validators.py` — extend these for HARD-02/HARD-03 test coverage
- Alembic migration path: `backend/migrations/versions/` (NOT `backend/alembic/versions/` — migrations directory)

---

## Open Questions

1. **Private subnets in Terraform**
   - What we know: `rds.tf` currently uses `aws_subnet.public[*].id`
   - What's unclear: Whether `aws_subnet.private` resources are defined in `network.tf`
   - Recommendation: Planner should include a verification step: read `deploy/terraform/qa/network.tf` before writing the RDS task; if private subnets don't exist, the task must create them first.

2. **ACM Certificate ARN**
   - What we know: CONTEXT.md says "leave cert ARN to be filled in — not blocking the PR"
   - What's unclear: Whether a cert exists in ACM for this account/domain
   - Recommendation: Use `count = var.acm_certificate_arn != "" ? 1 : 0` on the HTTPS listener so the Terraform can be applied without a cert. Document the variable in a comment.

3. **GitHub Secret Scanning tool choice (HARD-07)**
   - What we know: CONTEXT.md says "git-secrets or GitHub's built-in secret scanning"
   - What's unclear: Whether the GitHub repo has Advanced Security enabled (required for native secret scanning push protection)
   - Recommendation: Use `truffleHog` as a GitHub Actions step (no Advanced Security license required). Falls back to native if available. The planner should use `truffleHog` for CI and note that GitHub native scanning should be enabled in repo settings.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.3 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/ -x -q -m "not integration"` |
| Full suite command | `cd backend && pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARD-01 | Terraform validates after changes | smoke | `terraform validate` (in CI gate) | N/A — CI |
| HARD-02 | Startup fails with fallback SECRET_KEY | unit | `pytest tests/test_settings_guard.py -x` | ❌ Wave 0 |
| HARD-02 | Password policy rejects weak passwords | unit | `pytest tests/test_auth_routes.py -x -k password_policy` | ❌ Wave 0 (extend existing) |
| HARD-02 | Seed script generates non-hardcoded password | unit | `pytest tests/test_seed_admin.py -x` | ❌ Wave 0 |
| HARD-03 | Login sets HttpOnly cookie, not JSON token | unit | `pytest tests/test_auth_routes.py -x -k cookie` | ❌ Wave 0 (extend existing) |
| HARD-03 | get_current_user accepts cookie token | unit | `pytest tests/test_auth_security.py -x -k cookie` | ❌ Wave 0 |
| HARD-03 | Rate limiter rejects >10 login attempts/min | unit | `pytest tests/test_auth_routes.py -x -k rate_limit` | ❌ Wave 0 |
| HARD-04 | File list error returns generic message + correlation ID | unit | `pytest tests/test_api_files.py -x -k error_message` | ❌ Wave 0 |
| HARD-04 | get_file_url returns API path not file:// URI | unit | `pytest tests/test_storage_local.py -x -k no_file_uri` | ❌ Wave 0 |
| HARD-05 | CI gate job blocks deploy on lint failure | manual | Review deploy-test.yml `needs:` wiring | N/A — manual |
| HARD-06 | AuditLog DB write on login | unit | `pytest tests/test_audit_log.py -x -k login_write` | ❌ Wave 0 |
| HARD-06 | AuditLog table exists after migration | unit | `pytest tests/test_audit_log.py -x -k table_schema` | ❌ Wave 0 |
| HARD-07 | app-bundle.zip not in git index | manual | `git ls-files deploy/aws/eb/app-bundle.zip` → empty | N/A — manual |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/ -x -q -m "not integration"`
- **Per wave merge:** `cd backend && pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_settings_guard.py` — covers HARD-02 startup validation
- [ ] `backend/tests/test_seed_admin.py` — covers HARD-02 password generation
- [ ] `backend/tests/test_auth_security.py` — covers HARD-03 cookie extraction in get_current_user
- [ ] `backend/tests/test_api_files.py` — covers HARD-04 error message sanitization
- [ ] `backend/tests/test_storage_local.py` — covers HARD-04 file:// URL removal
- [ ] `backend/tests/test_audit_log.py` — covers HARD-06 DB write and schema

Extend existing files:
- [ ] `backend/tests/test_auth_routes.py` — add password policy tests, cookie-set tests, rate limit tests

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of all referenced files — audit.py, routes.py, security.py, files.py, settings.py, seed_admin.py, local.py, AuthContext.tsx, rds.tf, alb.tf, security-groups.tf, deploy-test.yml, conftest.py
- FastAPI official docs — cookie parameters, response cookies, CORSMiddleware
- Python stdlib docs — `secrets.token_urlsafe`
- Alembic 1.14 — migration file structure (verified from existing `60a8a67090c8_initial_schema.py`)

### Secondary (MEDIUM confidence)
- slowapi library docs — `https://slowapi.readthedocs.io/` — rate limiting pattern for FastAPI
- pip-audit PyPA project — CVE scanning for Python dependencies

### Tertiary (LOW confidence)
- truffleHog GitHub Actions usage — community pattern, widely used but verified via GitHub Actions Marketplace listing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt except slowapi; tools are well-established
- Architecture: HIGH — patterns derived directly from existing codebase code and official docs
- Pitfalls: HIGH — derived from actual code inspection (specific line numbers), not generalities

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable libraries; Terraform provider versions should be re-verified if > 30 days)
