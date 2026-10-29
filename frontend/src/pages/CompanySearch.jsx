import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import { TYPE_LABEL, logoColor } from "../jobUtils";

function SwipexCard({ c }) {
  return (
    <Link to={"/companies/" + c.id} className="glass job-card company-card">
      <div className="job-top">
        <div className="logo" style={{ background: logoColor(c.name) }}>
          {c.name.charAt(0)}
        </div>
        <div className="job-title">
          <h3>{c.name}</h3>
          <div className="muted small">{c.location || "Location not listed"}</div>
        </div>
        <span className={`badge ${c.verification_status}`}>{c.verification_status}</span>
      </div>
      <div className="meta">
        <span>{TYPE_LABEL[c.company_type] ?? c.company_type}</span>
        <span>{c.open_jobs} open jobs</span>
      </div>
    </Link>
  );
}

function PublicCard({ p }) {
  return (
    <Link to={"/companies/public/" + p.qid} className="glass job-card company-card">
      <div className="job-top">
        <div className="logo" style={{ background: logoColor(p.label) }}>
          {p.label.charAt(0)}
        </div>
        <div className="job-title">
          <h3>{p.label}</h3>
          <div className="muted small">{p.description}</div>
        </div>
        <span className="badge other">Public record</span>
      </div>
    </Link>
  );
}

export default function CompanySearch() {
  const [q, setQ] = useState("");
  const [featured, setFeatured] = useState([]);
  const [results, setResults] = useState({ companies: [], public: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const searching = q.trim().length >= 2;

  useEffect(() => {
    api
      .get("/explore/featured")
      .then(({ data }) => setFeatured(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const text = q.trim();
    if (text.length < 2) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(() => {
      api
        .get("/explore/search", { params: { q: text } })
        .then(({ data }) => {
          if (!cancelled) {
            setResults(data);
            setError("");
          }
        })
        .catch((err) => {
          if (!cancelled) setError(errorMessage(err));
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [q]);

  const nothing = searching && !loading && results.companies.length === 0 && results.public.length === 0;

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Companies</h2>
          <p className="muted">
            Search any company to see if it is real, its open jobs and the latest news.
          </p>
        </div>
      </div>

      <div className="search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Type a company name, for example Stripe or Infosys"
        />
      </div>

      {error && <div className="msg error">{error}</div>}

      {!searching && (
        <>
          <h4 className="sheet-title">Hiring on SwipeX</h4>
          <div className="jobs-grid">
            {featured.map((c) => (
              <SwipexCard key={c.id} c={c} />
            ))}
          </div>
        </>
      )}

      {searching && loading && <p className="muted">Searching...</p>}

      {searching && results.companies.length > 0 && (
        <>
          <h4 className="sheet-title">On SwipeX</h4>
          <div className="jobs-grid">
            {results.companies.map((c) => (
              <SwipexCard key={c.id} c={c} />
            ))}
          </div>
        </>
      )}

      {searching && results.public.length > 0 && (
        <>
          <h4 className="sheet-title">In public records</h4>
          <div className="jobs-grid">
            {results.public.map((p) => (
              <PublicCard key={p.qid} p={p} />
            ))}
          </div>
        </>
      )}

      {nothing && (
        <div className="glass card empty">
          <h3>No company found</h3>
          <p className="muted">Check the spelling, or try the company's full name.</p>
        </div>
      )}
    </section>
  );
}