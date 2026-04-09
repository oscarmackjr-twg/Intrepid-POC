# Stack Research: Internal Loan Purchase Operations Dashboard

**Research Type:** Project Research — Stack Dimension
**Date:** 2026-03-04
**Milestone:** Greenfield — Standard Stack Definition
**Question:** What is the standard 2025/2026 stack for an internal financial operations dashboard that processes loan tapes, runs Python business logic, generates PDFs, and sends emails?

---

## Summary Verdict

The fixed stack (React / Node.js / Python / PostgreSQL / AWS / Terraform) is well-suited for this use case. The decisions below are about which specific libraries to use within each layer. The biggest risks in this build are: (1) file upload reliability for large spreadsheets, (2) Node-to-Python job orchestration and error propagation, and (3) PDF generation fidelity for wire instruction documents. All three have clear, well-established solutions in 2025/2026.

---

## Layer 1: Frontend (React)

### Framework and Build

| Choice | Version | Rationale |
|--------|---------|-----------|
| **React** | 19.x | Fixed by project. React 19 ships with the `use` hook and improved Suspense — no breaking changes from 18. |
| **Vite** | 6.x | Faster dev server and build than CRA (deprecated) or webpack for an internal app. No SSR needed, so Next.js is overkill. |
| **TypeScript** | 5.x | Required for financial data handling. Strict mode enforced. Catches loan amount / rate type errors at compile time. |

### UI Component Library

**Use: shadcn/ui (Radix UI primitives) + Tailwind CSS 3.x**

Rationale:
- shadcn/ui components (Dialog, Table, Badge, Progress, Toast) are copy-owned, not imported from a versioned package. No breaking upstream dependency changes mid-project.
- Radix UI provides accessible, unstyled primitives — critical for data tables, modal confirmations, and step indicators.
- Tailwind CSS 3 is the standard in 2025 for internal tools. Avoids writing custom CSS for a dashboard that has no brand requirements.
- Alternative considered: MUI v6 — rejected because it imposes Material Design opinions that conflict with financial dashboard aesthetics, and the `sx` prop pattern is harder to maintain than Tailwind utility classes.

**Do NOT use:** Ant Design — it is a full opinionated framework that makes customization painful and has a large bundle size.

### State Management

**Use: TanStack Query (React Query) v5 + Zustand v5**

| Library | Purpose |
|---------|---------|
| **TanStack Query v5** | All server state: loan tape upload status, processing job polling, counterparty data fetching. Handles caching, background refetch, and stale-while-revalidate automatically. |
| **Zustand v5** | Local UI state only: current wizard step, selected loans, filter state. Lightweight with no boilerplate. |

Rationale:
- TanStack Query v5 (released late 2023, stable through 2025) eliminates manual `useEffect` fetch patterns. The `useQuery` + `useMutation` pattern maps perfectly to: upload tape → poll job status → display results.
- Do NOT use Redux for this. The data flow is simple (upload → process → review → send). Redux adds unnecessary boilerplate for a workflow that is mostly server-driven.
- Do NOT use React Context for server state. Context causes full subtree re-renders on every update — catastrophic for a table displaying 1,000 loan rows.

### File Upload

**Use: react-dropzone v14 + custom chunked upload to Node.js**

Rationale:
- `react-dropzone` is the standard for drag-and-drop file input in React (14M weekly downloads). Handles file type validation (`.xlsx`, `.csv`), size limits, and multi-file rejection.
- For ~1,000-loan spreadsheets, files will typically be 500KB–5MB. A single multipart POST to Node.js via `multer` is sufficient — no need for chunked upload or S3 presigned URLs at this scale.
- If files grow beyond 10MB (future state), switch to S3 presigned URL direct upload and notify Node.js of the S3 key post-upload.
- Do NOT use `<input type="file">` directly — react-dropzone adds critical UX feedback (drag state, rejection messages) that the ops team needs.

### Step-by-Step Workflow UI Pattern

**Use: local multi-step wizard with URL-synced step state**

Pattern:
```
/upload        → Step 1: Upload loan tape
/review        → Step 2: Review parsed loans, flag errors
/counterparty  → Step 3: Review counterparty tagging (prime/SFY)
/cashflows     → Step 4: Review calculated cashflows
/confirm       → Step 5: Confirm and trigger PDF + email send
```

Implementation:
- Each step is a separate route (React Router v7).
- Step progression is gated: user cannot advance until the previous step's server job is `COMPLETE`.
- TanStack Query polls job status every 2 seconds during Python processing steps.
- `react-hook-form` v7 handles any form inputs (override fields, email recipients) with Zod v3 schema validation.

Rationale for URL-based steps over in-memory wizard:
- Ops users can bookmark, refresh, and share links to a specific run in progress.
- Browser back button works naturally.
- Avoids the complexity of hydrating wizard state from localStorage.

**Do NOT use:** React stepper component libraries (MUI Stepper, react-step-wizard) — they obscure routing state and are hard to debug.

### Data Tables

**Use: TanStack Table v8**

Rationale:
- 1,000-row loan tables require virtualization. TanStack Table v8 with `@tanstack/react-virtual` handles this.
- Supports column sorting, filtering, row selection (for loan approval/rejection), and sticky headers.
- Headless — styled with Tailwind/shadcn, not locked to any design system.

---

## Layer 2: Node.js API / Middleware

### Runtime and Framework

| Choice | Version | Rationale |
|--------|---------|-----------|
| **Node.js** | 22 LTS | Fixed by project. Node 22 is the current LTS (October 2024). Use `--experimental-strip-types` if writing TypeScript without a build step, or compile with `tsc`. |
| **Express** | 5.x | The standard. Express 5 (released October 2024) adds async error handling natively — no more wrapping routes in `try/catch` or using `express-async-errors`. |
| **TypeScript** | 5.x | Same as frontend. Type-safe request/response shapes, especially for loan data structures. |

### File Upload Handling (Server Side)

**Use: multer v2 (middleware) + store to temp directory or S3**

```javascript
import multer from 'multer';
import multerS3 from 'multer-s3';

// For files under 10MB: temp disk storage
const upload = multer({
  dest: '/tmp/loan-tapes/',
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB
  fileFilter: (req, file, cb) => {
    const allowed = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/csv'];
    cb(null, allowed.includes(file.mimetype));
  }
});
```

Rationale:
- `multer` is the standard Node.js multipart form-data handler. v2 (released 2024) has improved TypeScript types.
- Store uploaded files to a temp directory on the EC2/ECS instance, then pass the file path to the Python worker. Python reads directly from disk — no serialization overhead.
- Alternatively: upload to S3 via `multer-s3` and pass the S3 key to Python. This is more resilient for multi-instance deployments but adds latency.

### Node-to-Python Orchestration

This is the most architecturally significant decision in the stack.

**Use: HTTP-based orchestration — Python as a FastAPI microservice on the same host or ECS sidecar**

Architecture:
```
React → POST /api/jobs/start → Node.js → POST http://localhost:8000/process → FastAPI (Python)
React → GET  /api/jobs/:id   → Node.js → reads job status from PostgreSQL
                                          (Python worker writes status/results to DB)
```

Rationale:
- A Python FastAPI service is cleaner than `child_process.spawn` for a persistent internal tool. Here is why:
  - `child_process.spawn` requires Node.js to manage Python subprocess lifecycle, handle stdout/stderr parsing, and deal with process exit codes. This becomes fragile for long-running jobs (30–60 seconds for 1,000 loans).
  - FastAPI gives Python its own process manager, structured error responses, and a testable API boundary.
  - The ops team can restart the Python service independently of the Node.js API.
- FastAPI on `localhost:8000` is simpler than a message queue (Redis/Celery) for this scale. The throughput is: one team, one run at a time, ~60 seconds per run. A queue is premature optimization.
- Do NOT use Celery + Redis unless concurrent multi-user job submission is required. It adds two infrastructure components (Redis + Celery workers) for no benefit at this scale.

Job status pattern (PostgreSQL-backed):
```sql
-- Node.js writes the job record, Python updates it
CREATE TABLE processing_jobs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status      TEXT CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETE', 'FAILED')),
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now(),
  input_s3_key TEXT,
  result_data  JSONB,
  error_message TEXT
);
```

Node.js polls / exposes:
- `POST /api/jobs` — creates job record, calls Python `/process` async
- `GET /api/jobs/:id` — returns current status from DB (React polls this every 2s)
- `GET /api/jobs/:id/results` — returns parsed loan results from `result_data` JSONB

**Alternative considered: BullMQ (Redis-backed job queue)**
- Rejected: adds Redis infrastructure dependency, over-engineered for single-team internal use.
- Reconsider if: multiple concurrent users submitting jobs simultaneously.

### Authentication / Authorization

**Use: AWS Cognito + JWT validation middleware (jwks-rsa + express-jwt)**

Rationale:
- Internal ops tool — no self-service registration needed. Cognito User Pools with an admin-created user list is the correct fit.
- Cognito integrates with the existing AWS infrastructure (Terraform-managed).
- All Node.js API routes protected by `express-jwt` middleware that validates the Cognito-issued JWT.
- Do NOT use Auth0 — it introduces a third-party SaaS dependency outside the AWS perimeter for an internal financial tool.
- Do NOT build custom JWT issuance — unnecessary complexity.

### API Validation

**Use: Zod v3 (shared with frontend)**

- Define Zod schemas for loan tape row shapes, job request bodies, and API responses.
- Share schema definitions between frontend and backend via a `packages/shared` workspace package (monorepo pattern).

---

## Layer 3: Python Processing Service

### Framework

| Choice | Version | Rationale |
|--------|---------|-----------|
| **FastAPI** | 0.115.x | Async HTTP server for receiving jobs from Node.js. Auto-generates OpenAPI docs. |
| **Uvicorn** | 0.32.x | ASGI server for FastAPI. Single worker is sufficient for this workload. |
| **Python** | 3.12 | Current stable. 3.13 released October 2024 but ecosystem compatibility still catching up in early 2025. Use 3.12. |

### Spreadsheet / Loan Tape Parsing

**Use: openpyxl v3.1.x (xlsx) + csv (stdlib)**

Rationale:
- `openpyxl` is the correct library for reading `.xlsx` files without Excel installed. Handles formula results (read-only mode), cell formatting, and named ranges.
- Do NOT use `xlrd` — it does not support `.xlsx`, only legacy `.xls`.
- Do NOT use `pandas` as the primary parsing library for loan tapes. Pandas is excellent for data science but adds significant startup overhead and DataFrame memory overhead for a 1,000-row business rules engine. Parse with `openpyxl`, apply rules with plain Python dicts/dataclasses.
- Exception: if the loan suitability rules require matrix calculations or statistical operations, use `pandas` for those specific calculations only, not for the initial parse.

### Business Rules Engine

**Use: plain Python dataclasses + Pydantic v2**

```python
from pydantic import BaseModel, validator
from decimal import Decimal

class LoanRecord(BaseModel):
    loan_id: str
    original_balance: Decimal
    interest_rate: Decimal
    ltv: Decimal
    fico_score: int
    property_state: str

    class Config:
        use_enum_values = True

class SuitabilityResult(BaseModel):
    loan_id: str
    is_suitable: bool
    rejection_reasons: list[str]
    counterparty: str | None  # 'prime' | 'SFY' | None
```

Rationale:
- Pydantic v2 (released 2023, standard in 2025) provides fast validation with clear error messages. Loan record validation errors surface as structured JSON back to Node.js.
- Business rules (LTV thresholds, FICO minimums, state restrictions) are plain Python functions operating on validated Pydantic models. No rules engine framework needed at this scale.
- Decimal (not float) for all monetary amounts — critical for financial calculations. Never use `float` for loan balances or interest rates.
- Do NOT use a rules engine library (Drools, easy-rules Python ports) — they add complexity without benefit for a finite, well-understood ruleset.

### Cashflow Calculation

**Use: numpy-financial v1.0.x + Decimal for monetary output**

Rationale:
- `numpy-financial` provides `npf.pmt()`, `npf.pv()`, `npf.fv()` for standard mortgage/loan cashflow calculations.
- Calculate with numpy floats internally, round to `Decimal` at output boundaries.
- Do NOT use `scipy` — overkill. Do NOT use a third-party loan amortization library — they rarely match the exact calculation conventions (day count, rounding) required by financial counterparties.

---

## Layer 4: PDF Generation

**Use: WeasyPrint v62.x**

Rationale:
- WeasyPrint renders HTML+CSS to PDF. Wire instruction documents are structured (tables, headers, amounts, routing numbers) — HTML templates are the most maintainable format for this.
- Template engine: **Jinja2 v3.x** — renders the HTML template with loan/cashflow data before passing to WeasyPrint.
- Produces pixel-accurate PDFs from CSS. Supports page breaks, headers, footers, and multi-page tables.
- Do NOT use ReportLab — it requires constructing PDFs programmatically (drawing text at x,y coordinates). Maintainability is poor when document layout changes.
- Do NOT use `pdfkit` (wkhtmltopdf wrapper) — wkhtmltopdf is abandoned, uses an old WebKit engine, and has known rendering bugs with modern CSS.
- Do NOT use Puppeteer/Playwright for PDF generation in the Python layer — introduces a Node.js/browser dependency into the Python service.

PDF generation pattern:
```python
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import tempfile

def generate_wire_instruction_pdf(loan_data: dict, output_path: str) -> str:
    env = Environment(loader=FileSystemLoader('templates/'))
    template = env.get_template('wire_instruction.html')
    html_content = template.render(**loan_data)

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        HTML(string=html_content).write_pdf(f.name)
        return f.name
```

PDF storage: save generated PDFs to S3 (`boto3`). Store the S3 key in PostgreSQL. Node.js generates a presigned URL for download. Do NOT serve PDFs directly from the Python service's filesystem.

---

## Layer 5: Email Delivery

**Use: AWS SES (Simple Email Service) via boto3**

Rationale:
- The stack is already AWS-native (Terraform). SES is the correct choice for a financial internal tool.
- SES supports: raw email with PDF attachments, HTML email bodies, sending from a verified domain, and delivery logs via CloudWatch.
- No third-party SaaS email service (SendGrid, Mailgun, Postmark) needed. This is important for financial data — wire instruction PDFs should not transit third-party servers.
- SES sending limits are more than sufficient for an internal ops tool (max ~100 emails/run).

Python SES pattern:
```python
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

def send_wire_instruction_email(
    recipient_emails: list[str],
    pdf_bytes: bytes,
    loan_summary: dict
) -> None:
    msg = MIMEMultipart()
    msg['Subject'] = f"Wire Instructions — {loan_summary['run_date']} ({loan_summary['loan_count']} loans)"
    msg['From'] = 'ops-noreply@yourdomain.com'
    msg['To'] = ', '.join(recipient_emails)

    # HTML body
    body = MIMEText(render_email_template(loan_summary), 'html')
    msg.attach(body)

    # PDF attachment
    attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
    attachment.add_header('Content-Disposition', 'attachment', filename='wire_instructions.pdf')
    msg.attach(attachment)

    ses = boto3.client('ses', region_name='us-east-1')
    ses.send_raw_email(
        Source='ops-noreply@yourdomain.com',
        Destinations=recipient_emails,
        RawMessage={'Data': msg.as_bytes()}
    )
```

Do NOT use: `smtplib` directly — brittle, requires SMTP server config. Do NOT use SendGrid/Mailgun — financial data should stay within the AWS perimeter.

---

## Layer 6: Database (PostgreSQL)

### Client / ORM

**Use: Drizzle ORM v0.38.x (Node.js) + psycopg v3.2.x (Python)**

Node.js side:
- **Drizzle ORM** with `drizzle-kit` for migrations. Rationale: Drizzle is TypeScript-first, schema-as-code, and generates raw SQL that is readable and auditable. This matters for financial systems where the DBA or auditor may need to inspect schema migrations.
- Do NOT use Prisma — Prisma's query engine (a Rust binary) adds deployment complexity in ECS/Lambda environments and has historically had issues with connection pooling.
- Do NOT use Sequelize — it is not TypeScript-first and encourages patterns that obscure the generated SQL.

Python side:
- **psycopg v3** (not psycopg2) — the current standard. Async support, binary protocol, better performance.
- Use raw SQL in Python for result writes. The Python service has a narrow, well-defined DB interaction: write job status, write results JSON, read counterparty config. ORMs are not needed here.

### Connection Pooling

**Use: PgBouncer (AWS RDS Proxy is acceptable alternative)**

- PgBouncer in transaction pooling mode. Reduces connection count from (Node.js workers + Python workers) to a manageable pool.
- For AWS RDS, use RDS Proxy (Terraform-managed) as an alternative — it provides IAM-authenticated connection pooling without a separate PgBouncer deployment.

### Schema Patterns for Financial Data

```sql
-- Monetary amounts: NUMERIC(18,6) — never FLOAT or DOUBLE PRECISION
-- Dates: DATE (not TIMESTAMP) for loan dates, maturity dates
-- IDs: UUID (gen_random_uuid()) — not serial integers, for external shareability
-- Audit: created_at / updated_at TIMESTAMPTZ on every table
-- Soft deletes: deleted_at TIMESTAMPTZ (never hard delete financial records)

CREATE TABLE loan_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_date        DATE NOT NULL,
    uploaded_by     TEXT NOT NULL,  -- Cognito user sub
    status          TEXT NOT NULL CHECK (status IN ('PENDING','PROCESSING','COMPLETE','FAILED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE TABLE loans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES loan_runs(id),
    loan_id_external TEXT NOT NULL,  -- ID from the uploaded tape
    original_balance NUMERIC(18,6) NOT NULL,
    interest_rate   NUMERIC(9,6) NOT NULL,
    ltv             NUMERIC(9,6),
    fico_score      SMALLINT,
    property_state  CHAR(2),
    is_suitable     BOOLEAN,
    rejection_reasons JSONB,
    counterparty    TEXT CHECK (counterparty IN ('prime', 'SFY')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cashflows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id         UUID NOT NULL REFERENCES loans(id),
    period_number   SMALLINT NOT NULL,
    payment_date    DATE NOT NULL,
    principal       NUMERIC(18,6) NOT NULL,
    interest        NUMERIC(18,6) NOT NULL,
    total_payment   NUMERIC(18,6) NOT NULL
);

CREATE TABLE wire_instructions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES loan_runs(id),
    counterparty    TEXT NOT NULL,
    pdf_s3_key      TEXT,
    email_sent_at   TIMESTAMPTZ,
    email_recipients JSONB,  -- array of strings
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Key schema rules:
- NUMERIC(18,6) for all monetary values — never FLOAT/DOUBLE.
- UUID primary keys everywhere — avoids integer ID enumeration.
- JSONB for flexible fields (rejection reasons, cashflow arrays) where schema may evolve.
- Soft deletes (deleted_at) — financial records are never hard deleted for audit purposes.

### Migrations

**Use: drizzle-kit (Node.js) for schema migrations**

- Migrations committed to git. Applied via CI/CD (GitHub Actions) before deployment.
- Do NOT use `db push` in production — always generate and apply explicit migration files.

---

## Layer 7: Infrastructure (AWS / Terraform)

### Compute

| Service | Use |
|---------|-----|
| **ECS Fargate** | Node.js API container + Python FastAPI container as a sidecar task |
| **ECR** | Container registry for both images |
| **ALB** | Application Load Balancer — routes to ECS service, terminates TLS |
| **CloudFront + S3** | React static frontend hosting |

Rationale for ECS Fargate over EC2:
- No server management. Fargate scales the task definition.
- The Node.js + Python sidecar pattern runs both containers in the same ECS task, enabling `localhost` communication without a service mesh.
- Do NOT use Lambda for the Python processing step. Lambda has a 15-minute timeout and memory limits that are challenging for batch processing 1,000 loans with WeasyPrint (which requires system fonts and GTK libraries).

### Storage

| Service | Use |
|---------|-----|
| **RDS PostgreSQL 16** | Primary database, Multi-AZ for production |
| **RDS Proxy** | Connection pooling (replaces PgBouncer) |
| **S3** | Uploaded loan tape files, generated PDFs |
| **Secrets Manager** | DB credentials, SES SMTP credentials |

### CI/CD

**Use: GitHub Actions**

- `test` → `build` → `push to ECR` → `terraform apply` → `ecs update-service`
- Drizzle migrations run as a one-off ECS task before the new service version comes up.

---

## What NOT to Use (Decision Log)

| Rejected | Reason |
|----------|--------|
| Next.js | SSR not needed for internal tool. Adds complexity (server components, hydration) without benefit. |
| Redux Toolkit | Overkill for this data flow. TanStack Query handles server state; Zustand handles UI state. |
| MUI / Ant Design | Opinionated design systems conflict with financial dashboard aesthetics; large bundle. |
| Celery + Redis | Premature for single-team, sequential job submission. Add if concurrency becomes a requirement. |
| child_process.spawn | Fragile for long-running Python jobs. FastAPI microservice is cleaner and independently restartable. |
| Prisma | Rust query engine binary complicates ECS deployment; connection pooling has known issues. |
| Lambda (Python) | 15-min timeout and memory constraints conflict with WeasyPrint system font requirements. |
| pdfkit / wkhtmltopdf | Abandoned project, old WebKit engine, modern CSS rendering bugs. |
| ReportLab | Requires programmatic PDF layout (x,y coordinates). Unmaintainable when layout changes. |
| Puppeteer for PDF | Introduces Node.js/Chromium into the Python service. Wrong layer. |
| SendGrid / Mailgun | Financial wire instruction PDFs should not transit third-party email servers. Use SES. |
| float / DOUBLE for money | IEEE 754 floating point causes rounding errors in financial calculations. Use NUMERIC/Decimal. |
| xlrd | Does not support .xlsx format (Excel 2007+). |
| pandas (primary parser) | Heavy startup cost; use openpyxl for parsing, pandas only if matrix math is needed. |
| Auth0 | Third-party SaaS outside AWS perimeter for an internal financial tool. Use Cognito. |
| serial integers as PKs | Enumerable; prefer UUIDs for financial record IDs. |

---

## Complete Dependency Manifest

### Frontend (package.json)

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.62.0",
    "@tanstack/react-table": "^8.20.0",
    "@tanstack/react-virtual": "^3.10.0",
    "zustand": "^5.0.0",
    "react-hook-form": "^7.54.0",
    "zod": "^3.24.0",
    "react-dropzone": "^14.3.0",
    "tailwindcss": "^3.4.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-progress": "^1.1.0",
    "@radix-ui/react-toast": "^1.2.0",
    "@radix-ui/react-table": "^1.0.0"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.7.0",
    "vitest": "^2.0.0",
    "@testing-library/react": "^16.0.0"
  }
}
```

### Backend Node.js (package.json)

```json
{
  "dependencies": {
    "express": "^5.0.0",
    "multer": "^2.0.0",
    "drizzle-orm": "^0.38.0",
    "pg": "^8.13.0",
    "aws-sdk": "^3.0.0",
    "zod": "^3.24.0",
    "jsonwebtoken": "^9.0.0",
    "jwks-rsa": "^3.1.0",
    "express-jwt": "^8.4.0",
    "axios": "^1.7.0",
    "uuid": "^11.0.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "drizzle-kit": "^0.28.0",
    "vitest": "^2.0.0"
  }
}
```

### Python (requirements.txt)

```
fastapi==0.115.6
uvicorn[standard]==0.32.1
pydantic==2.10.3
openpyxl==3.1.5
numpy-financial==1.0.0
numpy==2.2.0
weasyprint==62.3
jinja2==3.1.5
psycopg[binary]==3.2.3
boto3==1.35.86
python-multipart==0.0.20
```

---

## Architecture Diagram (Text)

```
[Ops User Browser]
       |
       | HTTPS
       v
[CloudFront + S3]  ──── React 19 SPA (Vite build)
       |
       | API calls (JWT in header)
       v
[ALB]
       |
       v
[ECS Fargate Task]
  ├── [Node.js Express 5 API :3000]
  │       ├── multer (file upload)
  │       ├── express-jwt (Cognito auth)
  │       ├── drizzle-orm → RDS PostgreSQL
  │       ├── axios → Python FastAPI :8000
  │       └── AWS SDK → S3, SES
  │
  └── [Python FastAPI :8000]  ← sidecar container
          ├── openpyxl (parse xlsx)
          ├── pydantic (validate loans)
          ├── business rules (plain Python)
          ├── numpy-financial (cashflows)
          ├── weasyprint + jinja2 (PDF)
          ├── boto3 → S3 (store PDFs)
          ├── boto3 → SES (send emails)
          └── psycopg3 → RDS PostgreSQL (write results)

[RDS PostgreSQL 16]  ← via RDS Proxy
[S3]                 ← loan tapes + generated PDFs
[Cognito]            ← auth
[SES]               ← email delivery
[Secrets Manager]   ← credentials
```

---

## Open Questions for Roadmap

1. **Concurrent job submissions:** If multiple ops users can submit runs simultaneously, add BullMQ + Redis for job queuing. Current design assumes sequential runs.
2. **Audit trail requirements:** Are loan processing decisions subject to regulatory audit? If yes, add an `audit_events` table and event sourcing for every status transition.
3. **PDF template ownership:** Who owns/updates wire instruction PDF templates? If business users need to edit templates without code deploys, consider storing Jinja2 templates in S3 or DB rather than the filesystem.
4. **Counterparty configuration:** Are prime/SFY routing rules static (hardcoded Python) or do they change? If they change, add a `counterparty_rules` table with admin UI.
5. **Email recipients:** Are recipients per-counterparty static config or user-entered per run? Affects the confirm step UI and the wire_instructions schema.

---

*Research complete. All library versions reflect current stable releases as of Q1 2026.*
