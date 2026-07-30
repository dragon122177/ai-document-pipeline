import {
  AlertTriangle,
  Check,
  ChevronRight,
  ClipboardCheck,
  ShieldAlert,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
} from "../components/Shared";
import { ConfidenceBadge } from "../components/StatusBadge";
import type { DocumentDetail, Review } from "../types";
import { errorMessage, formatDate, label } from "../utils";

export function ReviewPage() {
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [selected, setSelected] = useState<Review | null>(null);
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [notes, setNotes] = useState("");
  const [corrections, setCorrections] = useState("{}");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const result = await api.reviews();
      setReviews(result);
      setSelected((current) =>
        current ? result.find((item) => item.id === current.id) ?? result[0] ?? null : result[0] ?? null,
      );
      setError("");
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (!selected) {
      setDocument(null);
      return;
    }
    setNotes("");
    void api
      .document(selected.documentId)
      .then((result) => {
        setDocument(result);
        setCorrections(JSON.stringify(result.fields, null, 2));
      })
      .catch((caught) => setError(errorMessage(caught)));
  }, [selected]);

  const decide = async (decision: "APPROVED" | "REJECTED") => {
    if (!selected) return;
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(corrections) as Record<string, unknown>;
    } catch {
      setError("Corrections must be valid JSON.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const original = document?.fields ?? {};
      const changed = JSON.stringify(original) === JSON.stringify(parsed) ? {} : parsed;
      await api.decideReview(selected.id, decision, notes, changed);
      setDocument(null);
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Human oversight"
        title="Review queue"
        description="Verify low-confidence extractions and elevated risks before they enter downstream systems."
      />
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}
      {!reviews ? (
        <LoadingState label="Loading review queue" />
      ) : reviews.length === 0 ? (
        <EmptyState
          title="The review queue is clear"
          description="Documents that need a human decision will appear here."
        />
      ) : (
        <div className="review-workspace">
          <section className="panel review-list-panel">
            <header className="review-list-header">
              <div>
                <strong>{reviews.length} pending decisions</strong>
                <span>Oldest items appear first</span>
              </div>
              <ClipboardCheck size={20} />
            </header>
            <div className="review-list">
              {reviews.map((review) => (
                <button
                  key={review.id}
                  className={selected?.id === review.id ? "active" : ""}
                  onClick={() => setSelected(review)}
                >
                  <span className="review-file-icon">
                    {review.riskFlags.some((risk) => risk.severity === "HIGH") ? (
                      <ShieldAlert size={18} />
                    ) : (
                      <ClipboardCheck size={18} />
                    )}
                  </span>
                  <span>
                    <strong>{review.documentTitle}</strong>
                    <small>{label(review.category)} · {formatDate(review.createdAt)}</small>
                  </span>
                  <ConfidenceBadge confidence={review.confidence} />
                  <ChevronRight size={16} />
                </button>
              ))}
            </div>
          </section>

          <section className="panel review-detail">
            {!selected || !document ? (
              <LoadingState label="Loading source and extraction" />
            ) : (
              <>
                <header className="review-detail-header">
                  <div>
                    <p className="eyebrow">Decision workspace</p>
                    <h2>{selected.documentTitle}</h2>
                    <span>
                      Assigned to {selected.assignedToName ?? "review team"} ·{" "}
                      {label(selected.category)}
                    </span>
                  </div>
                  <ConfidenceBadge confidence={selected.confidence} />
                </header>

                {document.riskFlags.length > 0 && (
                  <div className="review-risk-strip">
                    <AlertTriangle size={18} />
                    <div>
                      <strong>{document.riskFlags.length} risk signals detected</strong>
                      <span>
                        {document.riskFlags.map((risk) => label(risk.code)).join(" · ")}
                      </span>
                    </div>
                  </div>
                )}

                <div className="review-columns">
                  <section>
                    <h3>Source preview</h3>
                    <pre className="document-preview review-preview">
                      {document.redactedText}
                    </pre>
                  </section>
                  <section>
                    <h3>Structured fields</h3>
                    <p>Edit the JSON only when the extracted values need correction.</p>
                    <textarea
                      className="json-editor"
                      value={corrections}
                      onChange={(event) => setCorrections(event.target.value)}
                      spellCheck={false}
                    />
                  </section>
                </div>

                <label className="field review-notes">
                  <span>Reviewer notes</span>
                  <textarea
                    rows={3}
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="Record the reason for this decision…"
                  />
                </label>
                <footer className="review-actions">
                  <span>Every decision is written to the immutable audit trail.</span>
                  <div>
                    <button
                      className="button danger"
                      disabled={busy}
                      onClick={() => void decide("REJECTED")}
                    >
                      <X size={16} /> Reject
                    </button>
                    <button
                      className="button success"
                      disabled={busy}
                      onClick={() => void decide("APPROVED")}
                    >
                      <Check size={16} /> Approve extraction
                    </button>
                  </div>
                </footer>
              </>
            )}
          </section>
        </div>
      )}
    </>
  );
}
