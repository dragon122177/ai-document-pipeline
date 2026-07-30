from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .database import Database
from .security import hash_password
from .utils import json_dump, new_id


def _timestamp(minutes_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def seed_database(database: Database) -> None:
    existing = database.fetch_one("SELECT COUNT(*) AS count FROM users")
    if existing and existing["count"]:
        return

    password_hash = hash_password("demo1234")
    users = [
        ("usr_admin", "admin@docuflux.demo", "Elena Park", password_hash, "ADMIN", _timestamp(40_000)),
        ("usr_analyst", "analyst@docuflux.demo", "Marcus Reed", password_hash, "ANALYST", _timestamp(39_000)),
        ("usr_reviewer", "reviewer@docuflux.demo", "Sofia Mendes", password_hash, "REVIEWER", _timestamp(38_000)),
    ]

    templates = [
        (
            "tpl_invoice",
            "Invoice extraction",
            "INVOICE",
            "Captures commercial invoice identifiers, totals, dates, and counterparties.",
            json_dump(
                [
                    {"key": "invoice_number", "label": "Invoice number", "required": True},
                    {"key": "invoice_date", "label": "Invoice date", "required": True},
                    {"key": "due_date", "label": "Due date", "required": False},
                    {"key": "total", "label": "Total amount", "required": True},
                    {"key": "currency", "label": "Currency", "required": True},
                    {"key": "vendor_email", "label": "Vendor email", "required": False},
                ]
            ),
            1,
            _timestamp(20_000),
        ),
        (
            "tpl_contract",
            "Contract review",
            "CONTRACT",
            "Extracts parties, effective dates, jurisdiction, and review clauses.",
            json_dump(
                [
                    {"key": "effective_date", "label": "Effective date", "required": True},
                    {"key": "parties", "label": "Parties", "required": True},
                    {"key": "term", "label": "Term", "required": False},
                    {"key": "jurisdiction", "label": "Jurisdiction", "required": False},
                    {"key": "renewal", "label": "Renewal clause", "required": False},
                ]
            ),
            1,
            _timestamp(19_000),
        ),
        (
            "tpl_resume",
            "Resume profile",
            "RESUME",
            "Captures candidate contact information, skills, and experience cues.",
            json_dump(
                [
                    {"key": "candidate_name", "label": "Candidate name", "required": True},
                    {"key": "email", "label": "Email", "required": True},
                    {"key": "phone", "label": "Phone", "required": False},
                    {"key": "skills", "label": "Skills", "required": True},
                ]
            ),
            1,
            _timestamp(18_000),
        ),
        (
            "tpl_report",
            "Financial report",
            "FINANCIAL_REPORT",
            "Extracts reporting period, revenue indicators, and notable risks.",
            json_dump(
                [
                    {"key": "reporting_period", "label": "Reporting period", "required": True},
                    {"key": "revenue", "label": "Revenue", "required": False},
                    {"key": "growth_rate", "label": "Growth rate", "required": False},
                ]
            ),
            1,
            _timestamp(17_000),
        ),
    ]

    documents = [
        {
            "id": "doc_invoice_1048",
            "title": "Northstar Cloud — Invoice 1048",
            "file_name": "northstar-invoice-1048.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 184_220,
            "sha256": "demo-invoice-1048",
            "status": "COMPLETED",
            "category": "INVOICE",
            "language": "English",
            "page_count": 2,
            "raw_text": "INVOICE #NS-1048. Northstar Cloud Services. Invoice date July 12, 2026. Due date August 11, 2026. Total USD $18,420.00. Billing contact accounts@northstar.example.",
            "redacted_text": "INVOICE #NS-1048. Northstar Cloud Services. Invoice date July 12, 2026. Due date August 11, 2026. Total USD $18,420.00. Billing contact [EMAIL_REDACTED].",
            "summary": "Northstar Cloud Services issued invoice NS-1048 for USD 18,420.00, due August 11, 2026.",
            "keywords": ["invoice", "northstar", "cloud", "total", "billing"],
            "entities": [{"type": "EMAIL", "value": "accounts@northstar.example", "start": 145, "end": 171, "confidence": 0.99}, {"type": "MONEY", "value": "$18,420.00", "start": 117, "end": 127, "confidence": 0.98}],
            "fields": {"invoice_number": "NS-1048", "invoice_date": "July 12, 2026", "due_date": "August 11, 2026", "total": "$18,420.00", "currency": "USD", "vendor_email": "accounts@northstar.example"},
            "risks": [],
            "tags": ["finance", "vendor"],
            "confidence": 0.96,
            "created_by": "usr_analyst",
            "minutes": 42,
        },
        {
            "id": "doc_contract_nda",
            "title": "Mutual NDA — Arcline & Ember",
            "file_name": "mutual-nda-arcline-ember.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size_bytes": 96_800,
            "sha256": "demo-contract-nda",
            "status": "NEEDS_REVIEW",
            "category": "CONTRACT",
            "language": "English",
            "page_count": 7,
            "raw_text": "MUTUAL NON-DISCLOSURE AGREEMENT between Arcline Labs and Ember Systems. Effective date July 1, 2026. This agreement automatically renews for successive twelve-month terms. Each party accepts unlimited liability for unauthorized disclosure. Governing law: State of New York.",
            "redacted_text": "MUTUAL NON-DISCLOSURE AGREEMENT between Arcline Labs and Ember Systems. Effective date July 1, 2026. This agreement automatically renews for successive twelve-month terms. Each party accepts unlimited liability for unauthorized disclosure. Governing law: State of New York.",
            "summary": "A mutual NDA between Arcline Labs and Ember Systems with automatic annual renewal and an unlimited-liability clause.",
            "keywords": ["agreement", "disclosure", "liability", "renewal", "confidential"],
            "entities": [{"type": "DATE", "value": "July 1, 2026", "start": 105, "end": 117, "confidence": 0.94}],
            "fields": {"effective_date": "July 1, 2026", "parties": ["Arcline Labs", "Ember Systems"], "term": "Successive twelve-month terms", "jurisdiction": "State of New York", "renewal": "Automatic"},
            "risks": [{"severity": "HIGH", "code": "UNLIMITED_LIABILITY", "message": "Unlimited liability language requires legal review."}, {"severity": "MEDIUM", "code": "AUTO_RENEWAL", "message": "The agreement contains an automatic renewal clause."}],
            "tags": ["legal", "nda"],
            "confidence": 0.84,
            "created_by": "usr_analyst",
            "minutes": 78,
        },
        {
            "id": "doc_report_q2",
            "title": "Q2 Regional Performance Report",
            "file_name": "q2-regional-performance.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1_420_500,
            "sha256": "demo-report-q2",
            "status": "APPROVED",
            "category": "FINANCIAL_REPORT",
            "language": "English",
            "page_count": 18,
            "raw_text": "Q2 2026 Regional Performance Report. Revenue reached $4.8 million, an increase of 12.4% year over year. Customer retention improved to 94%. Supply constraints remain the primary operational risk for the third quarter.",
            "redacted_text": "Q2 2026 Regional Performance Report. Revenue reached $4.8 million, an increase of 12.4% year over year. Customer retention improved to 94%. Supply constraints remain the primary operational risk for the third quarter.",
            "summary": "Q2 revenue reached $4.8 million with 12.4% annual growth and 94% retention; supply constraints remain the main risk.",
            "keywords": ["revenue", "regional", "retention", "supply", "quarter"],
            "entities": [{"type": "MONEY", "value": "$4.8 million", "start": 53, "end": 65, "confidence": 0.98}, {"type": "PERCENT", "value": "12.4%", "start": 82, "end": 87, "confidence": 0.99}],
            "fields": {"reporting_period": "Q2 2026", "revenue": "$4.8 million", "growth_rate": "12.4%"},
            "risks": [{"severity": "LOW", "code": "SUPPLY_CONSTRAINT", "message": "Supply constraints are identified as an operational risk."}],
            "tags": ["finance", "quarterly"],
            "confidence": 0.94,
            "created_by": "usr_admin",
            "minutes": 1_440,
        },
        {
            "id": "doc_resume_morgan",
            "title": "Morgan Lee — Platform Engineer",
            "file_name": "morgan-lee-resume.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 322_400,
            "sha256": "demo-resume-morgan",
            "status": "COMPLETED",
            "category": "RESUME",
            "language": "English",
            "page_count": 2,
            "raw_text": "Morgan Lee. Platform Engineer. Email morgan.lee@example.com. Phone +1 415 555 0184. Eight years of experience with Python, Kubernetes, PostgreSQL, AWS, Terraform, and distributed systems.",
            "redacted_text": "Morgan Lee. Platform Engineer. Email [EMAIL_REDACTED]. Phone [PHONE_REDACTED]. Eight years of experience with Python, Kubernetes, PostgreSQL, AWS, Terraform, and distributed systems.",
            "summary": "Platform engineer with eight years of experience across Python, Kubernetes, PostgreSQL, AWS, Terraform, and distributed systems.",
            "keywords": ["python", "kubernetes", "postgresql", "terraform", "platform"],
            "entities": [{"type": "EMAIL", "value": "morgan.lee@example.com", "start": 37, "end": 59, "confidence": 0.99}, {"type": "PHONE", "value": "+1 415 555 0184", "start": 67, "end": 82, "confidence": 0.97}],
            "fields": {"candidate_name": "Morgan Lee", "email": "morgan.lee@example.com", "phone": "+1 415 555 0184", "skills": ["Python", "Kubernetes", "PostgreSQL", "AWS", "Terraform"]},
            "risks": [{"severity": "MEDIUM", "code": "PII_DETECTED", "message": "Contact information should be protected before external sharing."}],
            "tags": ["recruiting", "engineering"],
            "confidence": 0.92,
            "created_by": "usr_analyst",
            "minutes": 340,
        },
    ]

    with database.transaction() as connection:
        connection.executemany(
            "INSERT INTO users (id,email,name,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
            users,
        )
        connection.executemany(
            "INSERT INTO templates (id,name,document_type,description,fields_json,active,created_at) VALUES (?,?,?,?,?,?,?)",
            templates,
        )

        for item in documents:
            created_at = _timestamp(item["minutes"])
            connection.execute(
                """
                INSERT INTO documents (
                  id,title,file_name,mime_type,size_bytes,sha256,storage_path,status,
                  category,language,page_count,raw_text,redacted_text,summary,
                  keywords_json,entities_json,fields_json,risk_flags_json,tags_json,
                  confidence,created_by,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    item["id"], item["title"], item["file_name"], item["mime_type"],
                    item["size_bytes"], item["sha256"], None, item["status"],
                    item["category"], item["language"], item["page_count"],
                    item["raw_text"], item["redacted_text"], item["summary"],
                    json_dump(item["keywords"]), json_dump(item["entities"]),
                    json_dump(item["fields"]), json_dump(item["risks"]),
                    json_dump(item["tags"]), item["confidence"], item["created_by"],
                    created_at, created_at,
                ),
            )
            connection.execute(
                "INSERT INTO document_fts (document_id,title,content) VALUES (?,?,?)",
                (item["id"], item["title"], item["raw_text"]),
            )
            for position, chunk_text in enumerate(
                [item["raw_text"][index:index + 500] for index in range(0, len(item["raw_text"]), 500)]
            ):
                connection.execute(
                    "INSERT INTO chunks (id,document_id,position,text,token_estimate,created_at) VALUES (?,?,?,?,?,?)",
                    (new_id("chk"), item["id"], position, chunk_text, max(1, len(chunk_text) // 4), created_at),
                )
            job_status = "NEEDS_REVIEW" if item["status"] == "NEEDS_REVIEW" else "COMPLETED"
            job_id = f"job_{item['id'][4:]}"
            connection.execute(
                """
                INSERT INTO jobs (
                  id,document_id,status,current_stage,progress,attempt,max_retries,
                  idempotency_key,error_message,created_at,started_at,finished_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (job_id, item["id"], job_status, "VALIDATION", 100, 1, 2, "seed", None, created_at, created_at, created_at),
            )
            connection.execute(
                "INSERT INTO job_events (id,job_id,stage,level,message,progress,created_at) VALUES (?,?,?,?,?,?,?)",
                (new_id("evt"), job_id, "COMPLETED", "INFO", "Document intelligence pipeline completed.", 100, created_at),
            )

        connection.execute(
            "INSERT INTO reviews (id,document_id,status,assigned_to,created_at) VALUES (?,?,?,?,?)",
            ("rev_contract_nda", "doc_contract_nda", "PENDING", "usr_reviewer", _timestamp(77)),
        )
        connection.execute(
            "INSERT INTO reviews (id,document_id,status,assigned_to,decided_by,notes,corrections_json,created_at,decided_at) VALUES (?,?,?,?,?,?,?,?,?)",
            ("rev_report_q2", "doc_report_q2", "APPROVED", "usr_reviewer", "usr_reviewer", "Metrics verified against the source report.", "{}", _timestamp(1_430), _timestamp(1_420)),
        )
        connection.execute(
            "INSERT INTO audit_events (id,actor_id,action,entity_type,entity_id,metadata_json,created_at) VALUES (?,?,?,?,?,?,?)",
            (new_id("aud"), "usr_reviewer", "DOCUMENT_APPROVED", "document", "doc_report_q2", json_dump({"reviewId": "rev_report_q2"}), _timestamp(1_420)),
        )
