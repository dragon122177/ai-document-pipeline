import {
  ArrowRight,
  CheckCircle2,
  FileScan,
  LockKeyhole,
  ScanText,
  Sparkles,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { errorMessage } from "../utils";

const demoAccounts = [
  { label: "Admin", email: "admin@docuflux.demo" },
  { label: "Analyst", email: "analyst@docuflux.demo" },
  { label: "Reviewer", email: "reviewer@docuflux.demo" },
];

export function LoginPage() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("admin@docuflux.demo");
  const [password, setPassword] = useState("demo1234");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/" replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="login-brand">
          <span className="brand-mark"><Sparkles size={21} /></span>
          <strong>DocuFlux</strong>
        </div>
        <div className="story-copy">
          <p className="eyebrow light">Intelligent document operations</p>
          <h1>Turn unstructured files into trusted business data.</h1>
          <p>
            Ingest, classify, extract, redact, search, and approve every
            document through one auditable workflow.
          </p>
          <div className="story-features">
            <span><FileScan size={18} /> Multi-format ingestion</span>
            <span><ScanText size={18} /> Structured AI extraction</span>
            <span><LockKeyhole size={18} /> PII-safe review flows</span>
          </div>
        </div>
        <div className="story-proof">
          <span><CheckCircle2 size={17} /> Provider-neutral architecture</span>
          <span>Built for explainability and human oversight.</span>
        </div>
      </section>

      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div>
            <p className="eyebrow">Secure workspace</p>
            <h2>Welcome back</h2>
            <p>Sign in to access the document operations console.</p>
          </div>
          <label className="field">
            <span>Email address</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && <div className="inline-error">{error}</div>}
          <button className="button primary login-submit" disabled={busy}>
            {busy ? "Authenticating…" : "Open workspace"}
            {!busy && <ArrowRight size={17} />}
          </button>
          <div className="demo-accounts">
            <span>Demo identities · password: demo1234</span>
            <div>
              {demoAccounts.map((account) => (
                <button
                  type="button"
                  key={account.email}
                  className={email === account.email ? "selected" : ""}
                  onClick={() => setEmail(account.email)}
                >
                  {account.label}
                </button>
              ))}
            </div>
          </div>
        </form>
        <p className="login-note">
          Fictional demo data only · no external AI credentials required
        </p>
      </section>
    </main>
  );
}
