import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import { TYPE_LABEL, logoColor } from "../jobUtils";

const LEVEL_LABEL = {
  strong: "Strong evidence",
  good: "Good evidence",
  limited: "Limited evidence",
};

function SignalIcon({ ok, known }) {
  const kind = !known ? "unknown" : ok ? "ok" : "no";
  const path = !known ? "M6 12h12" : ok ? "M5 12l4 4 10-10" : "M6 6l12 12M18 6L6 18";
  return (
    <span className={`signal-icon ${kind}`}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={path} />
      </svg>
    </span>
  );
}

export default function TrustSheet({ companyId, onClose }) {
  const [card, setCard] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get(`/companies/${companyId}/trust`)
      .then(({ data }) => {
        if (!cancelled) setCard(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const facts = card?.facts;
  const hiring = card?.hiring;
  const factItems = facts
    ? [
        ["Founded", facts.founded_year],
        ["Employees", facts.employees ? facts.employees.toLocaleString("en-IN") : null],
        ["Headquarters", facts.headquarters],
      ].filter(([, value]) => value)
    : [];

  return createPortal(
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="glass sheet" onClick={(e) => e.stopPropagation()}>
        <div className="grabber" />

        {!card && !error && <p className="muted">Checking this company...</p>}
        {error && <div className="msg error">{error}</div>}

        {card && (
          <>
            <div className="job-top">
              <div className="logo" style={{ background: logoColor(card.company.name) }}>
                {card.company.name.charAt(0)}
              </div>
              <div className="job-title">
                <h3>{card.company.name}</h3>
                <div className="muted small">
                  {TYPE_LABEL[card.company.company_type] ?? card.company.company_type}
                </div>
              </div>
              <span className={`level ${card.level}`}>{LEVEL_LABEL[card.level]}</span>
            </div>

            <h4 className="sheet-title">Evidence</h4>
            {card.signals
              .filter((s) => s.applicable)
              .map((s) => (
                <div className="signal" key={s.key}>
                  <SignalIcon ok={s.ok} known={s.known} />
                  <div>
                    <div>{s.label}</div>
                    {s.detail && <div className="muted small">{s.detail}</div>}
                  </div>
                </div>
              ))}

            {(factItems.length > 0 || facts.website || facts.wikipedia_url) && (
              <>
                <h4 className="sheet-title">Public facts</h4>
                {facts.description && <p className="muted small">{facts.description}</p>}
                <div className="facts">
                  {factItems.map(([label, value]) => (
                    <div className="fact" key={label}>
                      <span className="muted small">{label}</span>
                      <div>{value}</div>
                    </div>
                  ))}
                </div>
                <div className="actions" style={{ marginTop: "0.6rem" }}>
                  {facts.website && (
                    <a className="link" href={facts.website} target="_blank" rel="noreferrer">
                      Website
                    </a>
                  )}
                  {facts.wikipedia_url && (
                    <a className="link" href={facts.wikipedia_url} target="_blank" rel="noreferrer">
                      Wikipedia
                    </a>
                  )}
                  {facts.wikidata_url && (
                    <a className="link" href={facts.wikidata_url} target="_blank" rel="noreferrer">
                      Wikidata record
                    </a>
                  )}
                </div>
              </>
            )}

            <h4 className="sheet-title">Hiring on SwipeX</h4>
            {hiring ? (
              <div className="facts">
                <div className="fact">
                  <span className="muted small">Jobs posted</span>
                  <div>
                    {hiring.jobs_posted} ({hiring.open_jobs} open)
                  </div>
                </div>
                <div className="fact">
                  <span className="muted small">Applications</span>
                  <div>{hiring.applications}</div>
                </div>
                <div className="fact">
                  <span className="muted small">Got a response</span>
                  <div>
                    {hiring.responded}
                    {hiring.response_rate !== null ? ` (${Math.round(hiring.response_rate * 100)}%)` : ""}
                  </div>
                </div>
                <div className="fact">
                  <span className="muted small">Average response time</span>
                  <div>
                    {hiring.avg_response_days !== null ? `${hiring.avg_response_days} days` : "Not enough data yet"}
                  </div>
                </div>
              </div>
            ) : (
              <p className="muted small">
                This company's jobs come from its official job board, so you apply on its own site
                and hiring activity is not tracked here.
              </p>
            )}

            <p className="muted small disclaimer">
              These signals are evidence, not a guarantee. Public facts come from Wikidata and may
              be incomplete.
              {card.checked_at ? ` Checked on ${card.checked_at.slice(0, 10)}.` : ""}
            </p>
            <Link className="btn small" style={{ display: "inline-block", marginBottom: "0.8rem" }} to={"/companies/" + card.company.id} onClick={onClose}>View company page</Link>
            <button className="btn primary" onClick={onClose}>
              Close
            </button>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}