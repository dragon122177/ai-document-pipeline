# File map

This map connects every major behavior to the exact file that implements it.

## Repository root

| File | Why it exists |
|---|---|
| `README.md` | Product story, setup, screenshots-ready feature summary, and recruiter entry point |
| `.env.example` | Safe configuration names without real secrets |
| `.gitignore` | Prevents environments, secrets, uploads, databases, and builds from entering Git |
| `requirements.txt` | Reproducible Python runtime and test dependencies |
| `pyproject.toml` | Project metadata plus pytest and coverage configuration |
| `Dockerfile` | Non-root API container image |
| `compose.yaml` | API, web proxy, health check, and persistent volume |
| `Makefile` | Short local install, run, test, build, and Docker commands |
| `SECURITY.md` | Deployment boundaries and vulnerability reporting |
| `CONTRIBUTING.md` | Change and validation workflow |
| `LICENSE` | MIT usage terms |

## Backend application

| File | Responsibility |
|---|---|
| `backend/app/main.py` | Builds FastAPI, initializes services, configures CORS, handles validation errors, and registers routes |
| `backend/app/config.py` | Reads typed environment settings and resolves storage paths |
| `backend/app/database.py` | SQLite connections, WAL configuration, transactions, and query helpers |
| `backend/app/schema.sql` | Tables, constraints, indexes, foreign keys, and the FTS5 virtual table |
| `backend/app/seed.py` | Fictional users, templates, documents, jobs, reviews, and audit examples |
| `backend/app/models.py` | Pydantic request/response contracts and status enums |
| `backend/app/security.py` | PBKDF2 password hashing and HS256 signed token creation/validation |
| `backend/app/dependencies.py` | Bearer authentication and reusable role guards |
| `backend/app/storage.py` | File extension boundary, size limit, SHA-256 hashing, safe names, and local storage |
| `backend/app/extractors.py` | TXT, Markdown, CSV, JSON, PDF, and DOCX text extraction |
| `backend/app/intelligence.py` | Local analysis, remote provider interface, risk rules, confidence, and redaction |
| `backend/app/pipeline.py` | Job claim, stage progression, retries, chunks, indexing, review policy, and worker thread |
| `backend/app/events.py` | Thread-safe Server-Sent Event fan-out |
| `backend/app/audit.py` | Append-only application audit helper |
| `backend/app/serializers.py` | Converts database rows and JSON columns into API response objects |
| `backend/app/services.py` | Typed service container attached to the FastAPI application |
| `backend/app/utils.py` | IDs, timestamps, JSON handling, camelCase aliases, and safe slugs |

## Backend routes

| File | Endpoints |
|---|---|
| `backend/app/api/auth.py` | `/api/auth/login`, `/api/auth/me` |
| `backend/app/api/documents.py` | Document upload, text ingestion, list, detail, reprocess, and export |
| `backend/app/api/jobs.py` | Job list, job detail, and retry |
| `backend/app/api/reviews.py` | Pending reviews and governed decisions |
| `backend/app/api/search.py` | FTS5 query and ranked snippets |
| `backend/app/api/operations.py` | Dashboard, templates, and admin audit trail |
| `backend/app/api/events.py` | Authenticated SSE stream |
| `backend/app/api/common.py` | Shared document query and idempotent job helpers |

## Frontend

| File | Responsibility |
|---|---|
| `frontend/src/main.tsx` | React bootstrap, router, global styles, and auth provider |
| `frontend/src/App.tsx` | Protected routes and role-specific access |
| `frontend/src/api.ts` | Typed API client, session storage, downloads, errors, and SSE parser |
| `frontend/src/auth.tsx` | Session context, login, and logout |
| `frontend/src/types.ts` | Shared TypeScript domain models |
| `frontend/src/utils.ts` | Date, byte, label, snippet, and error formatting |
| `frontend/src/styles.css` | Complete visual system and responsive layouts |
| `frontend/src/hooks/useRealtime.ts` | Refreshes screens from pipeline/review events |
| `frontend/src/components/Layout.tsx` | Sidebar, navigation, role filtering, and workspace header |
| `frontend/src/components/UploadDialog.tsx` | Drag/drop file and pasted-text ingestion |
| `frontend/src/components/DocumentDrawer.tsx` | Summary, fields, entities, risks, redacted text, and timeline |
| `frontend/src/components/StatusBadge.tsx` | Consistent status and confidence presentation |
| `frontend/src/components/Shared.tsx` | Loading, empty, error, header, and progress primitives |
| `frontend/src/pages/LoginPage.tsx` | Secure login and three demo identities |
| `frontend/src/pages/DashboardPage.tsx` | Operational metrics and active work |
| `frontend/src/pages/DocumentsPage.tsx` | Searchable/filterable library |
| `frontend/src/pages/ReviewPage.tsx` | Human correction and approval workspace |
| `frontend/src/pages/SearchPage.tsx` | Corpus retrieval interface |
| `frontend/src/pages/TemplatesPage.tsx` | Output schema catalog |
| `frontend/src/pages/AuditPage.tsx` | Admin-only activity history and download |
| `frontend/nginx.conf` | SPA fallback and `/api` reverse proxy |
| `frontend/Dockerfile` | Multi-stage static web build |

## Tests and automation

| File | Coverage |
|---|---|
| `backend/tests/conftest.py` | Isolated database, app, client, and role sessions |
| `backend/tests/test_auth_and_permissions.py` | Login, invalid credentials, and role enforcement |
| `backend/tests/test_intelligence.py` | Classification, fields, PII redaction, and chunk overlap |
| `backend/tests/test_pipeline_api.py` | Idempotency, processing, review, upload, search, export, and metrics |
| `frontend/src/test/setup.ts` | Browser-like test setup and cleanup |
| `frontend/src/test/utils.test.ts` | UI formatting helpers |
| `frontend/src/test/components.test.tsx` | Status, ingestion modes, and demo-role interaction |
| `.github/workflows/ci.yml` | Python tests/coverage, TypeScript checks/tests/build, and Docker builds |

## Documentation and examples

| File | Purpose |
|---|---|
| `docs/ARCHITECTURE.md` | Component boundaries, state machine, review policy, and scale-out plan |
| `docs/API.md` | Routes, roles, payloads, errors, and generated OpenAPI locations |
| `docs/DEMO_SCRIPT.md` | A short interview demonstration |
| `docs/DECISIONS.md` | Honest technical trade-offs and next steps |
| `samples/invoice.txt` | Happy-path invoice extraction |
| `samples/contract.txt` | High-risk path into review |
| `samples/quarterly-report.json` | JSON extraction and search example |
