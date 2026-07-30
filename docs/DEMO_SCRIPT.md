# Five-minute demo script

## 1. Frame the problem

“DocuFlux turns unstructured business documents into trusted structured data.
The important part is not only extraction: it includes idempotent ingestion,
redaction, observability, human review, search, and an audit trail.”

## 2. Show the operations overview

Sign in with `admin@docuflux.demo` / `demo1234`.

Point out:

- category and confidence metrics;
- active pipeline progress;
- the existing contract in the review queue;
- the role-aware navigation and audit screen.

## 3. Run the happy path

Open **Ingest document** and upload `samples/invoice.txt`.

Open the document drawer while it processes. Show:

- the timeline moving through each stage;
- invoice classification and confidence;
- structured invoice fields;
- detected email and redacted safe preview;
- downloadable versioned JSON.

Explain that `backend/app/pipeline.py` owns the state machine and
`backend/app/intelligence.py` owns the provider contract and local engine.

## 4. Run the risk path

Upload `samples/contract.txt`.

The unlimited-liability rule is `HIGH`, so the validation stage routes the
result to review even when the classification confidence is acceptable. Open
**Review queue**, compare redacted source with extracted JSON, add a note, and
approve or reject.

Explain that `backend/app/api/reviews.py` writes the decision and correction,
while `backend/app/audit.py` records who acted.

## 5. Show retrieval and engineering quality

Search for `automatic renewal` or `quarterly revenue`. Mention that
`backend/app/schema.sql` configures FTS5 and the pipeline refreshes the index
only after successful processing.

Finish with:

- 12 backend tests and 6 frontend tests;
- Docker Compose for one-command startup;
- GitHub Actions for backend, frontend, and container validation;
- explicit limitations: local deterministic NLP, text-based PDFs only, and
  an in-process worker for the demo.
