from __future__ import annotations

import json
import math
import re
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class AnalysisResult:
    category: str
    language: str
    summary: str
    keywords: list[str]
    entities: list[dict[str, Any]]
    fields: dict[str, Any]
    risk_flags: list[dict[str, str]]
    confidence: float


class DocumentIntelligenceProvider(Protocol):
    name: str

    def analyze(self, text: str, title: str) -> AnalysisResult: ...


STOPWORDS = {
    "about", "after", "also", "and", "are", "been", "being", "between",
    "can", "could", "for", "from", "have", "into", "its", "more", "not",
    "of", "on", "or", "our", "shall", "that", "the", "their", "this",
    "through", "to", "was", "were", "will", "with", "within", "your",
    "como", "con", "del", "desde", "el", "ella", "en", "entre", "es",
    "esta", "este", "la", "las", "los", "para", "por", "que", "se", "una",
}

CATEGORY_SIGNALS = {
    "INVOICE": {
        "invoice": 4, "factura": 4, "subtotal": 2, "amount due": 3,
        "billing": 2, "purchase order": 2, "payment": 1,
    },
    "CONTRACT": {
        "agreement": 3, "contract": 4, "parties": 2, "governing law": 3,
        "confidential": 2, "liability": 2, "termination": 2, "clause": 2,
    },
    "RESUME": {
        "resume": 4, "curriculum": 4, "experience": 2, "skills": 3,
        "education": 2, "engineer": 1, "employment": 2,
    },
    "FINANCIAL_REPORT": {
        "quarter": 2, "revenue": 4, "financial": 3, "growth": 2,
        "margin": 2, "forecast": 2, "performance": 2,
    },
}

ENTITY_PATTERNS = [
    ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), 0.99),
    ("URL", re.compile(r"https?://[^\s)\]}]+", re.I), 0.97),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), 0.99),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]*?){13,16}\b"), 0.93),
    ("PHONE", re.compile(r"(?<!\d)(?:\+\d{1,3}[ -]?)?(?:\(?\d{3}\)?[ -]?)\d{3}[ -]\d{4}(?!\d)"), 0.94),
    ("MONEY", re.compile(r"(?i)(?:USD|EUR|MXN|JPY)?\s?[$€¥]\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:million|billion))?"), 0.97),
    ("PERCENT", re.compile(r"\b\d+(?:\.\d+)?%"), 0.98),
    ("DATE", re.compile(r"(?i)\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b"), 0.94),
]


class LocalIntelligenceProvider:
    name = "local-heuristic-v2"

    def analyze(self, text: str, title: str) -> AnalysisResult:
        normalized = re.sub(r"\s+", " ", text).strip()
        category, category_score = self._classify(normalized, title)
        entities = self._entities(normalized)
        fields = self._fields(category, normalized, title, entities)
        risks = self._risks(normalized, entities)
        keywords = self._keywords(normalized)
        summary = self._summary(normalized, keywords)
        language = self._language(normalized)
        completeness = min(1.0, len(fields) / 4)
        length_signal = min(1.0, math.log10(max(10, len(normalized))) / 4)
        confidence = min(
            0.98,
            0.56 + min(category_score, 8) * 0.035 + completeness * 0.08 + length_signal * 0.07,
        )
        if category == "GENERAL":
            confidence = min(confidence, 0.74)
        return AnalysisResult(
            category=category,
            language=language,
            summary=summary,
            keywords=keywords,
            entities=entities,
            fields=fields,
            risk_flags=risks,
            confidence=round(confidence, 3),
        )

    def _classify(self, text: str, title: str) -> tuple[str, int]:
        haystack = f"{title} {text}".lower()
        scores = {
            category: sum(
                weight * haystack.count(signal)
                for signal, weight in signals.items()
            )
            for category, signals in CATEGORY_SIGNALS.items()
        }
        category, score = max(scores.items(), key=lambda item: item[1])
        return (category, score) if score >= 3 else ("GENERAL", score)

    def _entities(self, text: str) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for entity_type, pattern, confidence in ENTITY_PATTERNS:
            for match in pattern.finditer(text):
                candidates.append(
                    {
                        "type": entity_type,
                        "value": match.group(0).strip(),
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": confidence,
                    }
                )
        candidates.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
        accepted: list[dict[str, Any]] = []
        for candidate in candidates:
            if any(
                candidate["start"] < item["end"]
                and candidate["end"] > item["start"]
                for item in accepted
            ):
                continue
            accepted.append(candidate)
        return accepted

    def _fields(
        self,
        category: str,
        text: str,
        title: str,
        entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        first = lambda entity_type: next(
            (item["value"] for item in entities if item["type"] == entity_type),
            None,
        )
        fields: dict[str, Any] = {}
        if category == "INVOICE":
            number = re.search(r"(?i)(?:invoice|factura)(?:\s*(?:number|no\.?|#))?\s*[:#-]?\s*([A-Z0-9-]{3,})", text)
            due = re.search(r"(?i)due\s+date\s*[:\-]?\s*([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})", text)
            dates = [item["value"] for item in entities if item["type"] == "DATE"]
            fields = {
                "invoice_number": number.group(1) if number else None,
                "invoice_date": dates[0] if dates else None,
                "due_date": due.group(1) if due else (dates[1] if len(dates) > 1 else None),
                "total": first("MONEY"),
                "currency": self._currency(text),
                "vendor_email": first("EMAIL"),
            }
        elif category == "CONTRACT":
            effective = re.search(r"(?i)effective\s+(?:date\s*)?[:\-]?\s*([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})", text)
            jurisdiction = re.search(r"(?i)(?:governing law|jurisdiction)\s*[:\-]?\s*([^.;\n]{3,80})", text)
            parties = re.search(r"(?i)between\s+([A-Z][A-Za-z0-9 &.-]{2,60})\s+and\s+([A-Z][A-Za-z0-9 &.-]{2,60})", text)
            fields = {
                "effective_date": effective.group(1) if effective else first("DATE"),
                "parties": [parties.group(1).strip(), parties.group(2).strip()] if parties else [],
                "jurisdiction": jurisdiction.group(1).strip() if jurisdiction else None,
                "renewal": "Automatic" if re.search(r"(?i)automat(?:ic|ically).{0,30}renew", text) else None,
                "term": self._match_value(text, r"(?i)(?:term|duration)\s*[:\-]?\s*([^.;\n]{3,80})"),
            }
        elif category == "RESUME":
            skills = [
                skill
                for skill in ["Python", "Java", "TypeScript", "React", "FastAPI", "AWS", "Azure", "Docker", "Kubernetes", "PostgreSQL", "Terraform", "Machine Learning"]
                if skill.lower() in text.lower()
            ]
            fields = {
                "candidate_name": title.split("—")[0].strip() if "—" in title else title,
                "email": first("EMAIL"),
                "phone": first("PHONE"),
                "skills": skills,
            }
        elif category == "FINANCIAL_REPORT":
            period = re.search(r"(?i)\b(Q[1-4]\s+20\d{2}|20\d{2}\s+(?:annual|year-end))\b", text)
            fields = {
                "reporting_period": period.group(1).upper() if period else None,
                "revenue": self._near_entity(text, entities, "MONEY", "revenue"),
                "growth_rate": self._near_entity(text, entities, "PERCENT", "growth"),
            }
        else:
            fields = {
                "title": title,
                "primary_email": first("EMAIL"),
                "primary_date": first("DATE"),
            }
        return {key: value for key, value in fields.items() if value not in (None, "", [])}

    def _risks(
        self, text: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        lowered = text.lower()
        risks: list[dict[str, str]] = []
        pii_types = {item["type"] for item in entities}
        if pii_types & {"SSN", "CREDIT_CARD"}:
            risks.append({"severity": "HIGH", "code": "SENSITIVE_PII", "message": "Highly sensitive personal or payment data was detected."})
        elif pii_types & {"EMAIL", "PHONE"}:
            risks.append({"severity": "MEDIUM", "code": "PII_DETECTED", "message": "Personal contact information should be protected before sharing."})
        if "unlimited liability" in lowered:
            risks.append({"severity": "HIGH", "code": "UNLIMITED_LIABILITY", "message": "Unlimited liability language requires specialist review."})
        if re.search(r"automat(?:ic|ically).{0,35}renew", lowered):
            risks.append({"severity": "MEDIUM", "code": "AUTO_RENEWAL", "message": "An automatic renewal clause was detected."})
        if "confidential" in lowered or "non-disclosure" in lowered:
            risks.append({"severity": "LOW", "code": "CONFIDENTIALITY", "message": "The document contains confidentiality obligations."})
        return risks

    def _keywords(self, text: str) -> list[str]:
        words = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ-]{2,}", text.lower())
        counts = Counter(
            word for word in words if word not in STOPWORDS and not word.isdigit()
        )
        return [word for word, _ in counts.most_common(8)]

    def _summary(self, text: str, keywords: list[str]) -> str:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if len(sentence.strip()) > 15
        ]
        if not sentences:
            return text[:420].strip()
        keyword_set = set(keywords)
        scored = []
        for index, sentence in enumerate(sentences[:40]):
            words = set(re.findall(r"[A-Za-zÀ-ÿ-]{3,}", sentence.lower()))
            score = len(words & keyword_set) + (1.2 if index == 0 else 0)
            scored.append((score, index, sentence))
        selected = sorted(scored, reverse=True)[:3]
        ordered = [item[2] for item in sorted(selected, key=lambda item: item[1])]
        return " ".join(ordered)[:700]

    def _language(self, text: str) -> str:
        lowered = f" {text.lower()} "
        spanish = sum(
            lowered.count(f" {word} ")
            for word in ("el", "la", "que", "para", "con", "una", "del")
        )
        english = sum(
            lowered.count(f" {word} ")
            for word in ("the", "and", "for", "with", "this", "from")
        )
        return "Spanish" if spanish > english + 1 else "English"

    @staticmethod
    def _currency(text: str) -> str:
        for currency in ("USD", "EUR", "MXN", "JPY"):
            if currency in text.upper():
                return currency
        if "€" in text:
            return "EUR"
        if "¥" in text:
            return "JPY"
        return "USD" if "$" in text else "Unknown"

    @staticmethod
    def _match_value(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _near_entity(
        text: str,
        entities: list[dict[str, Any]],
        entity_type: str,
        word: str,
    ) -> str | None:
        word_position = text.lower().find(word)
        options = [item for item in entities if item["type"] == entity_type]
        if not options:
            return None
        return min(
            options,
            key=lambda item: abs(item["start"] - word_position)
            if word_position >= 0
            else item["start"],
        )["value"]


class RemoteJsonProvider:
    """Provider-neutral adapter for a private JSON intelligence endpoint."""

    name = "remote-json-v1"

    def __init__(self, url: str, token: str | None) -> None:
        self.url = url
        self.token = token

    def analyze(self, text: str, title: str) -> AnalysisResult:
        payload = json.dumps({"title": title, "text": text}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            self.url, data=payload, headers=headers, method="POST"
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read())
        return AnalysisResult(**result)


def redact_text(text: str, entities: list[dict[str, Any]]) -> str:
    sensitive = {"EMAIL", "PHONE", "SSN", "CREDIT_CARD"}
    redacted = text
    for item in sorted(
        (entity for entity in entities if entity["type"] in sensitive),
        key=lambda entity: entity["start"],
        reverse=True,
    ):
        replacement = f"[{item['type']}_REDACTED]"
        redacted = (
            redacted[: item["start"]]
            + replacement
            + redacted[item["end"] :]
        )
    return redacted


def result_to_dict(result: AnalysisResult) -> dict[str, Any]:
    return asdict(result)
