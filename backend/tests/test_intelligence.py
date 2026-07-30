from app.intelligence import LocalIntelligenceProvider, redact_text
from app.pipeline import split_chunks


def test_invoice_classification_and_field_extraction() -> None:
    text = (
        "INVOICE #AC-901. Invoice date July 20, 2026. "
        "Due date August 20, 2026. Total USD $8,420.00. "
        "Questions: billing@acme.example."
    )
    result = LocalIntelligenceProvider().analyze(text, "Acme invoice")

    assert result.category == "INVOICE"
    assert result.fields["invoice_number"] == "AC-901"
    assert result.fields["total"].endswith("$8,420.00")
    assert result.fields["currency"] == "USD"
    assert result.confidence >= 0.8
    assert any(entity["type"] == "EMAIL" for entity in result.entities)


def test_sensitive_entities_are_redacted_without_changing_source() -> None:
    source = "Contact Jane at jane@example.com or 212-555-0198 today."
    result = LocalIntelligenceProvider().analyze(source, "Contact sheet")
    safe_text = redact_text(source, result.entities)

    assert "jane@example.com" in source
    assert "[EMAIL_REDACTED]" in safe_text
    assert "[PHONE_REDACTED]" in safe_text


def test_chunking_uses_overlap_for_retrieval_context() -> None:
    chunks = split_chunks("Sentence one. " * 180, size=240, overlap=40)

    assert len(chunks) > 5
    assert all(len(chunk) <= 241 for chunk in chunks)
