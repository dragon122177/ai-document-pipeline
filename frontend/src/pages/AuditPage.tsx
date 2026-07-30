import {
  Download,
  Fingerprint,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
} from "../components/Shared";
import type { AuditEvent } from "../types";
import { errorMessage, formatDate, label } from "../utils";

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void api
      .audit()
      .then(setEvents)
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  const download = () => {
    if (!events) return;
    const blob = new Blob([JSON.stringify(events, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "docuflux-audit-export.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Audit trail"
        description="Trace authentication, ingestion, pipeline, review, and export activity across the workspace."
        action={
          <button className="button secondary" onClick={download} disabled={!events?.length}>
            <Download size={16} /> Export log
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}
      {!events ? (
        <LoadingState label="Loading audit trail" />
      ) : events.length === 0 ? (
        <EmptyState
          title="No audit activity yet"
          description="Governed actions will appear as they occur."
        />
      ) : (
        <section className="panel audit-panel">
          <div className="audit-summary">
            <span><ShieldCheck size={19} /></span>
            <div>
              <strong>Append-only application events</strong>
              <p>{events.length} recent entries · newest first</p>
            </div>
          </div>
          <div className="audit-table">
            <div className="audit-row audit-head">
              <span>Timestamp</span>
              <span>Actor</span>
              <span>Action</span>
              <span>Target</span>
              <span>Context</span>
            </div>
            {events.map((event) => (
              <div className="audit-row" key={event.id}>
                <span>{formatDate(event.createdAt)}</span>
                <span>
                  <strong>{event.actorName ?? "System"}</strong>
                  <small>{event.actorEmail ?? "Internal worker"}</small>
                </span>
                <span className="audit-action">
                  <ShieldCheck size={14} /> {label(event.action)}
                </span>
                <span>
                  <strong>{label(event.entityType)}</strong>
                  <small className="mono"><Fingerprint size={11} /> {event.entityId}</small>
                </span>
                <code>{JSON.stringify(event.metadata)}</code>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
