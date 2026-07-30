# Security policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Contact the
repository owner privately with a reproducible description, affected version,
and proposed mitigation if available.

## Demonstration boundaries

DocuFlux ships with fictional data and development credentials. Before any
real deployment:

1. Replace `TOKEN_SECRET` with a strong secret managed outside the repository.
2. Remove or replace the seeded demo accounts in `backend/app/seed.py`.
3. Put the API behind TLS and an identity-aware reverse proxy.
4. Use encrypted object storage and an encrypted managed database.
5. Define retention, deletion, and least-privilege access policies.
6. Run malware scanning before extraction and add OCR in an isolated worker.

The local redaction rules are a safety aid, not a guarantee that every
sensitive value will be detected.
