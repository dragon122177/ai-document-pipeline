import {
  Asterisk,
  Boxes,
  FileJson,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import {
  ErrorBanner,
  LoadingState,
  PageHeader,
} from "../components/Shared";
import type { ExtractionTemplate } from "../types";
import { errorMessage, label } from "../utils";

export function TemplatesPage() {
  const [templates, setTemplates] = useState<ExtractionTemplate[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void api
      .templates()
      .then(setTemplates)
      .catch((caught) => setError(errorMessage(caught)));
  }, []);

  return (
    <>
      <PageHeader
        eyebrow="Extraction contracts"
        title="Document templates"
        description="Versionable field definitions keep downstream payloads predictable and explainable."
      />
      {error && <ErrorBanner message={error} />}
      {!templates ? (
        <LoadingState label="Loading extraction templates" />
      ) : (
        <div className="template-grid">
          {templates.map((template, index) => (
            <article className="template-card" key={template.id}>
              <header>
                <span className={`template-icon template-icon-${index + 1}`}>
                  {index % 2 === 0 ? <FileJson size={20} /> : <Boxes size={20} />}
                </span>
                <span className="active-pill"><i /> Active</span>
              </header>
              <p className="eyebrow">{label(template.documentType)}</p>
              <h2>{template.name}</h2>
              <p>{template.description}</p>
              <div className="template-fields">
                <span>Output schema · {template.fields.length} fields</span>
                {template.fields.map((field) => (
                  <div key={field.key}>
                    <code>{field.key}</code>
                    <span>{field.label}</span>
                    {field.required && <Asterisk size={12} aria-label="Required" />}
                  </div>
                ))}
              </div>
              <footer>
                <ShieldCheck size={15} />
                <span>Validated before export</span>
              </footer>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
