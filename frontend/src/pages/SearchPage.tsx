import { ArrowRight, FileSearch, Search, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { api } from "../api";
import { DocumentDrawer } from "../components/DocumentDrawer";
import { EmptyState, ErrorBanner, PageHeader } from "../components/Shared";
import { StatusBadge } from "../components/StatusBadge";
import type { SearchResult } from "../types";
import { cleanSnippet, errorMessage, formatDate, label } from "../utils";

const suggestions = ["invoice payment", "automatic renewal", "Python Kubernetes", "quarterly revenue"];

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const run = async (value: string) => {
    if (value.trim().length < 2) return;
    setBusy(true);
    setError("");
    setQuery(value);
    try {
      setResults(await api.search(value));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void run(query);
  };

  return (
    <>
      <PageHeader
        eyebrow="Indexed knowledge"
        title="Search across every document"
        description="Use the full-text index to find concepts inside source files, not only titles and tags."
      />
      {error && <ErrorBanner message={error} />}
      <section className="search-hero">
        <form onSubmit={submit}>
          <Search size={21} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search invoices, clauses, people, skills, or metrics…"
            autoFocus
          />
          <button className="button primary" disabled={busy || query.trim().length < 2}>
            {busy ? "Searching…" : "Search corpus"}
          </button>
        </form>
        <div className="search-suggestions">
          <span><Sparkles size={14} /> Try</span>
          {suggestions.map((suggestion) => (
            <button key={suggestion} onClick={() => void run(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
      </section>

      {results === null ? (
        <section className="search-explainer">
          <span><FileSearch size={23} /></span>
          <div>
            <h2>Search the extracted corpus</h2>
            <p>
              Every processed document is split into searchable chunks and
              indexed by SQLite FTS5. Results link back to the full extraction.
            </p>
          </div>
        </section>
      ) : results.length === 0 ? (
        <EmptyState
          title="No matching content"
          description="Try fewer words or a broader business concept."
        />
      ) : (
        <section className="search-results">
          <header>
            <p><strong>{results.length}</strong> results for “{query}”</p>
            <span>Ranked by full-text relevance</span>
          </header>
          {results.map((result) => (
            <button key={result.documentId} onClick={() => setSelected(result.documentId)}>
              <span className="result-icon"><FileSearch size={18} /></span>
              <span className="result-copy">
                <span>
                  <strong>{result.title}</strong>
                  <StatusBadge status={result.status} />
                </span>
                <p>{cleanSnippet(result.snippet)}</p>
                <small>{label(result.category)} · Updated {formatDate(result.updatedAt)}</small>
              </span>
              <ArrowRight size={17} />
            </button>
          ))}
        </section>
      )}
      <DocumentDrawer documentId={selected} onClose={() => setSelected(null)} />
    </>
  );
}
