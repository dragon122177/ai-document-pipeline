import {
  AlertTriangle,
  Check,
  Clock3,
  LoaderCircle,
  X,
} from "lucide-react";
import { label } from "../utils";

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase();
  const icon =
    normalized === "APPROVED" || normalized === "COMPLETED" ? (
      <Check size={12} />
    ) : normalized === "REJECTED" || normalized === "FAILED" ? (
      <X size={12} />
    ) : normalized === "PROCESSING" ? (
      <LoaderCircle className="spin" size={12} />
    ) : normalized === "NEEDS_REVIEW" ? (
      <AlertTriangle size={12} />
    ) : (
      <Clock3 size={12} />
    );
  return (
    <span className={`status-badge status-${normalized.toLowerCase()}`}>
      {icon}
      {label(normalized)}
    </span>
  );
}

export function ConfidenceBadge({
  confidence,
}: {
  confidence: number | null;
}) {
  if (confidence === null) return <span className="muted">—</span>;
  const percentage = Math.round(confidence * 100);
  const tone =
    percentage >= 90 ? "high" : percentage >= 78 ? "medium" : "low";
  return <span className={`confidence confidence-${tone}`}>{percentage}%</span>;
}
