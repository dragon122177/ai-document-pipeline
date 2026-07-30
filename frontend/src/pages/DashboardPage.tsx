import {
  ArrowRight,
  BookOpenCheck,
  BrainCircuit,
  CircleGauge,
  FileCheck2,
  FileStack,
  Plus,
  ScanSearch,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { DocumentDrawer } from "../components/DocumentDrawer";
import {
  ErrorBanner,
  LoadingState,
  PageHeader,
  ProgressBar,
} from "../components/Shared";
import { ConfidenceBadge, StatusBadge } from "../components/StatusBadge";
import { UploadDialog } from "../components/UploadDialog";
import { useRealtime } from "../hooks/useRealtime";
import type { Dashboard } from "../types";
import { errorMessage, formatDate, label } from "../utils";

const metricIcons = [FileStack, FileCheck2, BookOpenCheck, CircleGauge];

export function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    try {
      setData(await api.dashboard());
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

  const metricItems = useMemo(
    () =>
      data
        ? [
            {
              label: "Total documents",
              value: data.metrics.totalDocuments,
              detail: "Across the workspace",
            },
            {
              label: "Ready for use",
              value: data.metrics.readyDocuments,
              detail: "Completed or approved",
            },
            {
              label: "Pending review",
              value: data.metrics.pendingReview,
              detail: "Human decision required",
            },
            {
              label: "Avg. confidence",
              value: `${data.metrics.averageConfidence}%`,
              detail: `${data.metrics.activeJobs} active pipeline jobs`,
            },
          ]
        : [],
    [data],
  );
  const canWrite = user?.role === "ADMIN" || user?.role === "ANALYST";
  const maxCategory = Math.max(
    1,
    ...(data?.categoryDistribution.map((item) => item.count) ?? [1]),
  );

  return (
    <>
      <PageHeader
        eyebrow="Document intelligence"
        title="Good afternoon, let’s move documents forward."
        description="Monitor extraction quality, active pipelines, and decisions that need a human."
        action={
          canWrite ? (
            <button className="button primary" onClick={() => setUploadOpen(true)}>
              <Plus size={17} /> Ingest document
            </button>
          ) : undefined
        }
      />
      {error && <ErrorBanner message={error} onRetry={() => void load()} />}
      {!data ? (
        <LoadingState />
      ) : (
        <div className="dashboard-grid">
          <section className="metric-grid full-span">
            {metricItems.map((metric, index) => {
              const Icon = metricIcons[index];
              return (
                <article className="metric-card" key={metric.label}>
                  <span className={`metric-icon metric-icon-${index + 1}`}>
                    <Icon size={19} />
                  </span>
                  <div>
                    <span>{metric.label}</span>
                    <strong>{metric.value}</strong>
                    <small>{metric.detail}</small>
                  </div>
                </article>
              );
            })}
          </section>

          <section className="panel panel-wide">
            <header className="panel-header">
              <div>
                <p className="eyebrow">Recent activity</p>
                <h2>Document flow</h2>
              </div>
              <Link to="/documents" className="text-link">
                View all <ArrowRight size={15} />
              </Link>
            </header>
            <div className="document-table">
              <div className="table-row table-head">
                <span>Document</span>
                <span>Type</span>
                <span>Status</span>
                <span>Confidence</span>
                <span>Updated</span>
              </div>
              {data.recentDocuments.map((document) => (
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
                  <span>{label(document.category)}</span>
                  <span><StatusBadge status={document.status} /></span>
                  <span><ConfidenceBadge confidence={document.confidence} /></span>
                  <span>{formatDate(document.updatedAt)}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="panel category-panel">
            <header className="panel-header">
              <div>
                <p className="eyebrow">Corpus makeup</p>
                <h2>Categories</h2>
              </div>
              <BrainCircuit size={20} className="panel-icon" />
            </header>
            <div className="category-bars">
              {data.categoryDistribution.map((item, index) => (
                <div key={item.category}>
                  <div>
                    <span><i style={{ "--bar-index": index } as React.CSSProperties} />{label(item.category)}</span>
                    <strong>{item.count}</strong>
                  </div>
                  <div className="category-track">
                    <span
                      style={{
                        width: `${Math.max(8, (item.count / maxCategory) * 100)}%`,
                        "--bar-index": index,
                      } as React.CSSProperties}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <header className="panel-header">
              <div>
                <p className="eyebrow">Live orchestration</p>
                <h2>Pipeline jobs</h2>
              </div>
              <ScanSearch size={20} className="panel-icon" />
            </header>
            {data.activeJobs.length ? (
              <div className="job-list">
                {data.activeJobs.map((job) => (
                  <div key={job.id}>
                    <div>
                      <span className="job-stage">{label(job.currentStage)}</span>
                      <strong>{job.documentTitle}</strong>
                      <small>Attempt {job.attempt + 1} of {job.maxRetries}</small>
                    </div>
                    <span>{job.progress}%</span>
                    <ProgressBar value={job.progress} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="compact-empty">
                <span><BrainCircuit size={20} /></span>
                <div><strong>Pipeline is clear</strong><p>No queued or active jobs.</p></div>
              </div>
            )}
          </section>

          <section className="panel">
            <header className="panel-header">
              <div>
                <p className="eyebrow">Human in the loop</p>
                <h2>Review queue</h2>
              </div>
              <Link to="/review" className="text-link">
                Open queue <ArrowRight size={15} />
              </Link>
            </header>
            {data.reviewQueue.length ? (
              <div className="review-mini-list">
                {data.reviewQueue.map((review) => (
                  <div key={review.id}>
                    <span className="review-mini-icon">
                      <BookOpenCheck size={17} />
                    </span>
                    <div>
                      <strong>{review.documentTitle}</strong>
                      <span>{label(review.category)} · {review.assignedToName ?? "Unassigned"}</span>
                    </div>
                    <ConfidenceBadge confidence={review.confidence} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="compact-empty">
                <span><FileCheck2 size={20} /></span>
                <div><strong>Everything reviewed</strong><p>No pending decisions.</p></div>
              </div>
            )}
          </section>
        </div>
      )}
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
