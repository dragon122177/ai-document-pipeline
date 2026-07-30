# API reference

FastAPI generates the complete OpenAPI schema at runtime:

- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- OpenAPI JSON: `GET /openapi.json`

This project does not commit a generated `openapi.yaml`; the application code
is the source of truth and CI verifies it through tests.

All protected routes require:

```http
Authorization: Bearer <token>
```

## Authentication and system

| Method | Route | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/health` | Public | Database, provider, worker, and version status |
| `POST` | `/api/auth/login` | Public | Create an expiring signed session |
| `GET` | `/api/auth/me` | Authenticated | Resolve the current identity |
| `GET` | `/api/events` | Authenticated | Server-Sent Event stream |

## Documents

| Method | Route | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/documents` | Any role | Filter and list documents |
| `POST` | `/api/documents/text` | Admin, Analyst | Ingest pasted text |
| `POST` | `/api/documents/upload` | Admin, Analyst | Upload an allowed file |
| `GET` | `/api/documents/{id}` | Any role | Full extraction, review, chunks, and timeline |
| `POST` | `/api/documents/{id}/process` | Admin, Analyst | Queue a new processing run |
| `GET` | `/api/documents/{id}/export` | Any role | Download a versioned JSON result |

The upload route accepts `multipart/form-data` fields `file`, `title`, `tags`,
and `idempotency_key`. File extensions are checked before storage. The text
route accepts:

```json
{
  "title": "Vendor invoice 2048",
  "content": "INVOICE #2048 ...",
  "tags": ["finance", "vendor"],
  "idempotencyKey": "vendor-2048"
}
```

## Pipeline and review

| Method | Route | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/jobs` | Any role | Recent processing jobs |
| `GET` | `/api/jobs/{id}` | Any role | One job and its progress |
| `POST` | `/api/jobs/{id}/retry` | Admin, Analyst | Reset a failed job |
| `GET` | `/api/reviews` | Admin, Reviewer | Review queue |
| `POST` | `/api/reviews/{id}/decision` | Admin, Reviewer | Approve/reject with corrections |

Decision payload:

```json
{
  "decision": "APPROVED",
  "notes": "Verified against the source.",
  "corrections": {
    "invoice_number": "NS-2048"
  }
}
```

## Operations

| Method | Route | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/dashboard` | Any role | Metrics and current work |
| `GET` | `/api/search?q=...` | Any role | Ranked FTS5 retrieval |
| `GET` | `/api/templates` | Any role | Active extraction schemas |
| `GET` | `/api/audit` | Admin | Recent governed activity |

## Error behavior

Validation errors use a stable envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request payload is invalid.",
    "details": []
  }
}
```

Domain errors use FastAPI's `detail` field, for example
`unsupported_file_type:.exe`, `ocr_required`, or
`insufficient_permissions`.
