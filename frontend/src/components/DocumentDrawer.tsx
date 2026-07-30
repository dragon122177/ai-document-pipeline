import {
  AlertTriangle,
  Braces,
  Download,
  FileText,
  Fingerprint,
  RefreshCw,
  ShieldCheck,
  Tags,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import type { DocumentDetail } from "../types";
import { errorMessage, formatBytes, formatDate, label } from "../utils";
import { ErrorBanner, LoadingState, ProgressBar } from "./Shared";
import { ConfidenceBadge, StatusBadge } from "./StatusBadge";

type Tab = "overview" | "fields" | "entities" | "redacted" | "timeline";

export function DocumentDrawer({
  documentId,
  onClose,
  refreshKey = 0,
}: {
  documentId: string | null;
  onClose: () => void;
  refreshKey?: number;
}) {
  const { user } = useAuth();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState("");
  const [actionBusy, setActionBusy] = useState(false);

  useEffect(() => {
    if (!documentId) return;
    let active = true;
    setError("");
    void api
      .document(documentId)
      .then((result) => active && setDocument(result))
      .catch((caught) => active && setError(errorMessage(caught)));
    return () => {
      active = false;
    };
  }, [documentId, refreshKey]);

  useEffect(() => {
    if (documentId) setTab("overview");
  }, [documentId]);

  if (!documentId) return null;
  const canWrite = user?.role === "ADMIN" || user?.role === "ANALYST";

  const reprocess = async () => {
    setActionBusy(true);
    try {
      await api.process(documentId);
      setDocument(await api.document(documentId));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <div className="drawer-layer" role="presentation" onMouseDown={onClose}>
      <aside
        className="document-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Document details"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-header">
          <div>
            <p className="eyebrow">Document intelligence</p>
            <h2>{document?.title ?? "Loading document…"}</h2>
          </div>
          <button className="icon-button" aria-label="Close" onClick={onClose}>
            <X size={20} />
          </button>
        </header>

        {error && <ErrorBanner message={error} />}
        {!document ? (
          <LoadingState label="Opening document" />
        ) : (
          <>
            <div className="document-meta-bar">
              <StatusBadge status={document.status} />
              <span>{label(document.category)}</span>
              <span>{formatBytes(document.sizeBytes)}</span>
              <ConfidenceBadge confidence={document.confidence} />
            </div>

            {document.job &&
              ["QUEUED", "PROCESSING"].includes(document.job.status) && (
                <div className="live-job">
                  <div>
                    <strong>{label(document.job.currentStage)}</strong>
                    <span>{document.job.progress}%</span>
                  </div>
                  <ProgressBar value={document.job.progress} />
                </div>
              )}

            <div className="drawer-tabs" role="tablist">
              {(
                [
                  ["overview", "Overview"],
                  ["fields", "Fields"],
                  ["entities", "Entities"],
                  ["redacted", "Safe text"],
                  ["timeline", "Timeline"],
                ] as Array<[Tab, string]>
              ).map(([value, text]) => (
                <button
                  key={value}
                  className={tab === value ? "active" : ""}
                  onClick={() => setTab(value)}
                  role="tab"
                >
                  {text}
                </button>
              ))}
            </div>

            <div className="drawer-content">
              {tab === "overview" && (
                <div className="drawer-stack">
                  <section className="detail-section">
                    <div className="section-heading">
                      <FileText size={17} />
                      <h3>AI summary</h3>
                    </div>
                    <p className="summary-text">
                      {document.summary || "Summary will appear after processing."}
                    </p>
                  </section>

                  {document.riskFlags.length > 0 && (
                    <section className="detail-section">
                      <div className="section-heading">
                        <AlertTriangle size={17} />
                        <h3>Risk signals</h3>
                      </div>
                      <div className="risk-list">
                        {document.riskFlags.map((risk) => (
                          <div
                            className={`risk-card risk-${risk.severity.toLowerCase()}`}
                            key={risk.code}
                          >
                            <span>{risk.severity}</span>
                            <div>
                              <strong>{label(risk.code)}</strong>
                              <p>{risk.message}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  <section className="detail-section">
                    <div className="section-heading">
                      <Tags size={17} />
                      <h3>Keywords</h3>
                    </div>
                    <div className="tag-list">
                      {document.keywords.length ? (
                        document.keywords.map((keyword) => (
                          <span key={keyword}>{keyword}</span>
                        ))
                      ) : (
                        <p className="muted">No keywords extracted yet.</p>
                      )}
                    </div>
                  </section>

                  <section className="source-facts">
                    <div><span>File</span><strong>{document.fileName}</strong></div>
                    <div><span>Pages</span><strong>{document.pageCount}</strong></div>
                    <div><span>Language</span><strong>{document.language ?? "—"}</strong></div>
                    <div><span>Owner</span><strong>{document.createdByName}</strong></div>
                    <div><span>Updated</span><strong>{formatDate(document.updatedAt)}</strong></div>
                    <div className="hash-fact">
                      <span><Fingerprint size={13} /> SHA-256</span>
                      <strong title={document.sha256}>{document.sha256.slice(0, 16)}…</strong>
                    </div>
                  </section>
                </div>
              )}

              {tab === "fields" && (
                <section className="detail-section">
                  <div className="section-heading">
                    <Braces size={17} />
                    <h3>Structured extraction</h3>
                    <span className="section-count">
                      {Object.keys(document.fields).length} fields
                    </span>
                  </div>
                  <div className="field-table">
                    {Object.entries(document.fields).map(([key, value]) => (
                      <div key={key}>
                        <span>{label(key)}</span>
                        <strong>
                          {Array.isArray(value)
                            ? value.join(", ")
                            : typeof value === "object"
                              ? JSON.stringify(value)
                              : String(value)}
                        </strong>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {tab === "entities" && (
                <section className="detail-section">
                  <div className="section-heading">
                    <ShieldCheck size={17} />
                    <h3>Detected entities</h3>
                    <span className="section-count">{document.entities.length}</span>
                  </div>
                  <div className="entity-list">
                    {document.entities.map((entity, index) => (
                      <div key={`${entity.start}-${index}`}>
                        <span className="entity-type">{label(entity.type)}</span>
                        <strong>{entity.value}</strong>
                        <span>{Math.round(entity.confidence * 100)}%</span>
                      </div>
                    ))}
                    {!document.entities.length && (
                      <p className="muted">No named entities detected.</p>
                    )}
                  </div>
                </section>
              )}

              {tab === "redacted" && (
                <section className="detail-section">
                  <div className="section-heading">
                    <ShieldCheck size={17} />
                    <h3>Redacted safe preview</h3>
                  </div>
                  <pre className="document-preview">
                    {document.redactedText || "Redacted text will appear after processing."}
                  </pre>
                </section>
              )}

              {tab === "timeline" && (
                <section className="detail-section">
                  <div className="section-heading">
                    <RefreshCw size={17} />
                    <h3>Pipeline timeline</h3>
                  </div>
                  <div className="timeline">
                    {document.events.map((event) => (
                      <div key={event.id}>
                        <i className={`timeline-dot timeline-${event.level.toLowerCase()}`} />
                        <div>
                          <strong>{label(event.stage)}</strong>
                          <p>{event.message}</p>
                        </div>
                        <span>{event.progress}%</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>

            <footer className="drawer-footer">
              <button
                className="button secondary"
                onClick={() =>
                  void api.exportDocument(
                    document.id,
                    `${document.id}-analysis.json`,
                  )
                }
              >
                <Download size={16} /> Export JSON
              </button>
              {canWrite && (
                <button
                  className="button primary"
                  disabled={actionBusy || ["QUEUED", "PROCESSING"].includes(document.status)}
                  onClick={() => void reprocess()}
                >
                  <RefreshCw size={16} /> Reprocess
                </button>
              )}
            </footer>
          </>
        )}
      </aside>
    </div>
  );
}
