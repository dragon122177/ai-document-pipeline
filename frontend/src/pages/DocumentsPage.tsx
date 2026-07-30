import {
  FilePlus2,
  FileStack,
  Filter,
  Plus,
  Search,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { DocumentDrawer } from "../components/DocumentDrawer";
import {
  EmptyState,
  ErrorBanner,
  LoadingState,
  PageHeader,
} from "../components/Shared";
import { ConfidenceBadge, StatusBadge } from "../components/StatusBadge";
import { UploadDialog } from "../components/UploadDialog";
import { useRealtime } from "../hooks/useRealtime";
import type { DocumentItem } from "../types";
import { errorMessage, formatBytes, formatDate, label } from "../utils";

const statuses = [
  "ALL",
  "PROCESSING",
  "COMPLETED",
  "NEEDS_REVIEW",
  "APPROVED",
  "FAILED",
];

export function DocumentsPage() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [error, setError] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    try {
      setDocuments(await api.documents());
      setError("");
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  useRealtime(
    useCallback(() => {
      void load();
      setRefreshKey((value) => value + 1);
    }, [load]),
  );

  const filtered = useMemo(
    () =>
      (documents ?? []).filter((document) => {
        const matchesStatus = status === "ALL" || document.status === status;
        const needle = query.toLowerCase();
        const matchesQuery =
          !needle ||
          document.title.toLowerCase().includes(needle) ||
          document.fileName.toLowerCase().includes(needle) ||
          document.tags.some((tag) => tag.includes(needle));
        return matchesStatus && matchesQuery;
      }),
    [documents, query, status],
  );
  const canWrite = user?.role === "ADMIN" || user?.role === "ANALYST";

  return (
    <>
      <PageHeader
        eyebrow="Source of truth"
        title="Document library"
        description="Inspect every source file, extracted result, risk signal, and processing state."
        action={
          canWrite ? (
            <button className="button primary" onClick={() => setUploadOpen(true)}>
              <Plus size={17} /> Ingest document
            </button>
          ) : undefined
        }
      />
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}
      <section className="panel library-panel">
        <div className="library-toolbar">
          <label className="search-input">
            <Search size={17} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter by title, file name, or tag"
            />
          </label>
          <div className="filter-control">
            <Filter size={16} />
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              {statuses.map((value) => (
                <option value={value} key={value}>{label(value)}</option>
              ))}
            </select>
          </div>
          <span className="result-count">{filtered.length} documents</span>
        </div>
        {!documents ? (
          <LoadingState label="Loading documents" />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No documents match"
            description="Change the filters or start a new pipeline run."
            action={
              canWrite ? (
                <button className="button secondary" onClick={() => setUploadOpen(true)}>
                  <FilePlus2 size={16} /> Add document
                </button>
              ) : undefined
            }
          />
        ) : (
          <div className="document-table library-table">
            <div className="table-row table-head">
              <span>Document</span>
              <span>Classification</span>
              <span>Status</span>
              <span>Confidence</span>
              <span>Size</span>
              <span>Updated</span>
            </div>
            {filtered.map((document) => (
              <button
                className="table-row"
                key={document.id}
                onClick={() => setSelected(document.id)}
              >
                <span className="document-cell">
                  <i><FileStack size={16} /></i>
                  <span>
                    <strong>{document.title}</strong>
                    <small>{document.fileName}</small>
                  </span>
                </span>
                <span>
                  <strong className="plain-value">{label(document.category)}</strong>
                  <small>{document.language ?? "Pending"}</small>
                </span>
                <span><StatusBadge status={document.status} /></span>
                <span><ConfidenceBadge confidence={document.confidence} /></span>
                <span>{formatBytes(document.sizeBytes)}</span>
                <span>{formatDate(document.updatedAt)}</span>
              </button>
            ))}
          </div>
        )}
      </section>
      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onCreated={(id) => {
          setSelected(id);
          void load();
        }}
      />
      <DocumentDrawer
        documentId={selected}
        refreshKey={refreshKey}
        onClose={() => setSelected(null)}
      />
    </>
  );
}
