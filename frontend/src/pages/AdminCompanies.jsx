import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { TYPE_LABEL, logoColor } from "../jobUtils";

const FILTERS = [
  ["pending", "Pending"],
  ["unverified", "Unverified"],
  ["verified", "Verified"],
  ["rejected", "Rejected"],
  ["all", "All"],
];
const LABEL = {
  verified: "Verified",
  pending: "Pending",
  unverified: "Unverified",
  rejected: "Rejected",
};

export default function AdminCompanies() {
  const [filter, setFilter] = useState("pending");
  const [companies, setCompanies] = useState([]);
  const [notes, setNotes] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/companies", {
        params: filter === "all" ? {} : { status: filter },
      });
      setCompanies(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [filter]);

  async function decide(company, decision) {
    setError("");
    try {
      await api.post(`/admin/companies/${company.id}/decision`, {
        decision,
        note: (notes[company.id] ?? "").trim() || null,
      });
      setNotes((n) => ({ ...n, [company.id]: "" }));
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Companies</h2>
          <p className="muted">Only verified companies show jobs to job seekers.</p>
        </div>
      </div>

      <div className="filter-bar">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            className={filter === key ? "fchip on" : "fchip"}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div className="msg error">{error}</div>}
      {loading && <p className="muted">Loading...</p>}
      {!loading && companies.length === 0 && (
        <div className="glass card empty">
          <h3>Nothing here</h3>
          <p className="muted">No companies with this status.</p>
        </div>
      )}

      <div className="jobs-grid">
        {companies.map((c) => (
          <article className="glass job-card" key={c.id}>
            <div className="job-top">
              <div className="logo" style={{ background: logoColor(c.name) }}>
                {c.name.charAt(0)}
              </div>
              <div className="job-title">
                <h3>{c.name}</h3>
                <div className="muted small">
                  {[c.location, c.founded_year ? `Founded ${c.founded_year}` : null]
                    .filter(Boolean)
                    .join("  |  ")}
                </div>
              </div>
              <span className={`badge ${c.verification_status}`}>
                {LABEL[c.verification_status]}
              </span>
            </div>

            <div className="meta">
              <span>{TYPE_LABEL[c.company_type] ?? c.company_type}</span>
              <span>{c.jobs_count} jobs</span>
              <span>Source: {c.source}</span>
              <span>{c.owner_email ? `Recruiter: ${c.owner_email}` : "No recruiter linked"}</span>
            </div>

            {c.website && (
              <a className="link" href={c.website} target="_blank" rel="noreferrer">
                {c.website}
              </a>
            )}

            {c.verification_note && (
              <div className="verify-note">
                <span className="muted small">Note</span>
                <div>{c.verification_note}</div>
              </div>
            )}

            <input
              value={notes[c.id] ?? ""}
              onChange={(e) => setNotes({ ...notes, [c.id]: e.target.value })}
              placeholder="Note (required when rejecting)"
              maxLength={1000}
            />
            <div className="actions">
              <button className="btn small primary-inline" onClick={() => decide(c, "verified")}>
                Verify
              </button>
              <button className="btn small danger" onClick={() => decide(c, "rejected")}>
                Reject
              </button>
              <button className="btn small" onClick={() => decide(c, "unverified")}>
                Reset
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}