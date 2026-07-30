# Engineering decisions

## Deterministic local intelligence by default

The repository must work during a review without external credentials, network
latency, or provider spend. `LocalIntelligenceProvider` therefore implements a
transparent baseline. `DocumentIntelligenceProvider` keeps the integration
boundary open for a private model gateway.

**Trade-off:** the local rules are explainable and testable but less capable
than a production language model on novel document types.

## SQLite plus FTS5

SQLite makes the demo durable with no infrastructure and supports transactions,
constraints, WAL, and full-text search.

**Trade-off:** it is not the intended store for high concurrent write volume.
PostgreSQL plus managed object storage is the natural production migration.

## Jobs table before a message broker

The jobs table provides idempotency, attempts, stage visibility, and recovery.
One in-process worker polls and claims rows transactionally.

**Trade-off:** horizontal workers need a production queue and distributed
locking strategy. The state model is designed to survive that migration.

## Source text and redacted text remain separate

The raw extraction is never overwritten. A safe preview is generated from
entity offsets and stored independently, so reviewers can reason about what
was protected.

**Trade-off:** any raw-text access remains sensitive and must be protected by
stronger deployment controls for regulated data.

## Policy-based human review

Low confidence and high-severity risks trigger review. A reviewer can correct
fields and record a decision, and the application appends an audit event.

**Trade-off:** the thresholds are global in the demo. Production policy should
be configurable by organization, document type, and downstream action.

## Runtime OpenAPI instead of a committed generated file

FastAPI generates `/openapi.json`, `/docs`, and `/redoc` from the actual route
and Pydantic contracts.

**Trade-off:** consumers that require a versioned static specification would
add a CI export and compatibility check. The generated artifact should not be
edited manually.

## Explicit OCR limitation

Text-based PDF extraction is supported. An image-only PDF fails with
`ocr_required`; the project does not simulate OCR.

**Next step:** route scanned files to an isolated OCR service, store confidence
per page, and retain the original image coordinates for review.
