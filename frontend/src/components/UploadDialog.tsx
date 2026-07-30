import {
  FileText,
  UploadCloud,
  X,
} from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { api } from "../api";
import { errorMessage } from "../utils";

export function UploadDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (documentId: string, deduplicated: boolean) => void;
}) {
  const [mode, setMode] = useState<"file" | "text">("file");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  const reset = () => {
    setFile(null);
    setTitle("");
    setTags("");
    setContent("");
    setError("");
  };

  const close = () => {
    if (busy) return;
    reset();
    onClose();
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const key = crypto.randomUUID();
      const result =
        mode === "file"
          ? await (() => {
              if (!file) throw new Error("Choose a document first");
              const form = new FormData();
              form.append("file", file);
              form.append("title", title);
              form.append("tags", tags);
              form.append("idempotency_key", key);
              return api.upload(form);
            })()
          : await api.createText({
              title,
              content,
              tags: tags
                .split(",")
                .map((tag) => tag.trim())
                .filter(Boolean),
              idempotencyKey: key,
            });
      reset();
      onClose();
      onCreated(result.document.id, result.deduplicated);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-layer" role="presentation" onMouseDown={close}>
      <section
        className="modal upload-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-heading"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="modal-header">
          <div>
            <p className="eyebrow">New pipeline run</p>
            <h2 id="upload-heading">Ingest a document</h2>
            <p>Upload a supported file or paste source text directly.</p>
          </div>
          <button className="icon-button" aria-label="Close" onClick={close}>
            <X size={20} />
          </button>
        </header>

        <div className="segmented-control">
          <button
            className={mode === "file" ? "selected" : ""}
            onClick={() => setMode("file")}
            type="button"
          >
            <UploadCloud size={16} /> File upload
          </button>
          <button
            className={mode === "text" ? "selected" : ""}
            onClick={() => setMode("text")}
            type="button"
          >
            <FileText size={16} /> Paste text
          </button>
        </div>

        <form onSubmit={submit}>
          {mode === "file" ? (
            <button
              type="button"
              className={`dropzone ${file ? "has-file" : ""}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                setFile(event.dataTransfer.files[0] ?? null);
              }}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".txt,.md,.csv,.json,.pdf,.docx"
                hidden
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <span className="dropzone-icon"><UploadCloud size={23} /></span>
              <strong>{file ? file.name : "Drop a document here"}</strong>
              <span>
                {file
                  ? `${(file.size / 1024).toFixed(1)} KB selected`
                  : "PDF, DOCX, TXT, Markdown, CSV, or JSON · max 12 MB"}
              </span>
            </button>
          ) : (
            <label className="field">
              <span>Document content</span>
              <textarea
                rows={9}
                required
                minLength={20}
                value={content}
                onChange={(event) => setContent(event.target.value)}
                placeholder="Paste an invoice, contract, report, resume, or other business document…"
              />
            </label>
          )}

          <div className="form-grid">
            <label className="field">
              <span>Display title</span>
              <input
                required={mode === "text"}
                minLength={3}
                maxLength={160}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder={mode === "file" ? "Optional — uses file name" : "e.g. Vendor invoice 2048"}
              />
            </label>
            <label className="field">
              <span>Tags</span>
              <input
                value={tags}
                onChange={(event) => setTags(event.target.value)}
                placeholder="finance, vendor, urgent"
              />
            </label>
          </div>
          {error && <div className="inline-error">{error}</div>}
          <footer className="modal-footer">
            <span>Processing starts automatically after ingestion.</span>
            <div>
              <button type="button" className="button secondary" onClick={close}>
                Cancel
              </button>
              <button className="button primary" disabled={busy}>
                {busy ? "Starting pipeline…" : "Start pipeline"}
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}
