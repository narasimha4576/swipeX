import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import CompanyLink from "./CompanyLink";
import { LEVEL_LABEL, TYPE_LABEL, logoColor, salary, timeAgo } from "../jobUtils";

const STATUSES = [
  ["saved", "Saved"],
  ["applied", "Applied"],
  ["shortlisted", "Shortlisted"],
  ["interview", "Interview"],
  ["rejected", "Rejected"],
];
const STATUS_LABEL = Object.fromEntries(STATUSES);

const HINTS = {
  saved: "Swipe right on Discover to save jobs. They wait for you here.",
  applied: "Jobs you applied to will show up here.",
  shortlisted: "When a recruiter shortlists you, the job moves here.",
  interview: "Interview invitations will show up here.",
  rejected: "Rejected applications are kept here so you can learn from them.",
};

export default function Applications() {
  const [items, setItems] = useState([]);
  const [resumes, setResumes] = useState([]);
  const [tab, setTab] = useState("saved");
  const [applyingId, setApplyingId] = useState(null);
  const [externalId, setExternalId] = useState(null);
  const [resumeId, setResumeId] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const [apps, res] = await Promise.all([api.get("/applications"), api.get("/resumes")]);
      setItems(apps.data);
      setResumes(res.data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function startApply(app) {
    setError("");
    setOk("");
    if (app.job.source !== "native") {
      if (!app.job.apply_url) {
        setError("This job has no apply link");
        return;
      }
      window.open(app.job.apply_url, "_blank", "noopener,noreferrer");
      setApplyingId(null);
      setExternalId(app.id);
      return;
    }
    setExternalId(null);
    setApplyingId(app.id);
    const pick = resumes.find((r) => r.is_default) ?? resumes[0];
    setResumeId(pick ? String(pick.id) : "");
  }

  async function confirmApply(app) {
    setError("");
    try {
      await api.post("/applications/apply", {
        job_id: app.job.id,
        resume_id: Number(resumeId),
      });
      setApplyingId(null);
      setOk(`You applied to ${app.job.title} at ${app.job.company.name}`);
      setTab("applied");
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function markApplied(app) {
    setError("");
    try {
      await api.post(`/applications/${app.id}/mark-applied`);
      setExternalId(null);
      setOk(`Marked as applied: ${app.job.title} at ${app.job.company.name}`);
      setTab("applied");
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(app) {
    setError("");
    setOk("");
    try {
      await api.delete(`/applications/${app.id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const counts = items.reduce((acc, a) => {
    acc[a.status] = (acc[a.status] ?? 0) + 1;
    return acc;
  }, {});
  const shown = items.filter((a) => a.status === tab);

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Applications</h2>
          <p className="muted">Track every job from saved to offer.</p>
        </div>
      </div>

      <div className="filter-bar">
        {STATUSES.map(([key, label]) => (
          <button
            key={key}
            className={tab === key ? "fchip on" : "fchip"}
            onClick={() => setTab(key)}
          >
            {label} ({counts[key] ?? 0})
          </button>
        ))}
      </div>

      {error && <div className="msg error">{error}</div>}
      {ok && <div className="msg ok">{ok}</div>}
      {loading && <p className="muted">Loading...</p>}

      {!loading && shown.length === 0 && (
        <div className="glass card empty">
          <h3>Nothing here yet</h3>
          <p className="muted">{HINTS[tab]}</p>
        </div>
      )}

      <div className="jobs-grid">
        {shown.map((a) => {
          const official = a.job.source !== "native";
          return (
            <article className="glass job-card" key={a.id}>
              <div className="job-top">
                <div className="logo" style={{ background: logoColor(a.job.company.name) }}>
                  {a.job.company.name.charAt(0)}
                </div>
                <div className="job-title">
                  <h3><Link className="title-link" to={"/jobs/" + a.job.id}>{a.job.title}</Link></h3>
                  <CompanyLink company={a.job.company} />
                </div>
                <span className={`badge ${a.status}`}>{STATUS_LABEL[a.status]}</span>
              </div>

              <div className="meta">
                <span>{a.job.is_remote ? "Remote" : a.job.location}</span>
                <span>{LEVEL_LABEL[a.job.experience_level] ?? a.job.experience_level}</span>
                <span>{TYPE_LABEL[a.job.company.company_type] ?? a.job.company.company_type}</span>
                {official && <span>Official listing</span>}
              </div>

              <div className="salary">{salary(a.job)}</div>

              <div className="muted small">
                Updated {timeAgo(a.updated_at)}
                {a.resume_name ? `  |  Resume: ${a.resume_name}` : ""}
                {official && a.status === "applied" ? "  |  Applied on the company site" : ""}
              </div>

              {a.status === "saved" && applyingId !== a.id && externalId !== a.id && (
                <div className="actions">
                  <button className="btn small primary-inline" onClick={() => startApply(a)}>
                    {official ? "Apply on company site" : "Apply"}
                  </button>
                  <button className="btn small" onClick={() => remove(a)}>
                    Remove
                  </button>
                </div>
              )}

              {externalId === a.id && (
                <div className="apply-panel">
                  <p className="muted">
                    Finish your application on the company page that just opened. Then come back
                    and confirm.
                  </p>
                  <div className="actions">
                    <button className="btn small primary-inline" onClick={() => markApplied(a)}>
                      Yes, I applied
                    </button>
                    <button className="btn small" onClick={() => startApply(a)}>
                      Open the page again
                    </button>
                    <button className="btn small" onClick={() => setExternalId(null)}>
                      Not yet
                    </button>
                  </div>
                </div>
              )}

              {applyingId === a.id && (
                <div className="apply-panel">
                  {resumes.length === 0 ? (
                    <p className="muted">
                      Upload a resume first.{" "}
                      <Link className="link" to="/profile">
                        Go to Profile
                      </Link>
                    </p>
                  ) : (
                    <>
                      <label className="field">
                        <span>Apply with</span>
                        <select value={resumeId} onChange={(e) => setResumeId(e.target.value)}>
                          {resumes.map((r) => (
                            <option key={r.id} value={r.id}>
                              {r.version_name}
                              {r.is_default ? " (default)" : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="actions">
                        <button
                          className="btn small primary-inline"
                          onClick={() => confirmApply(a)}
                        >
                          Confirm apply
                        </button>
                        <button className="btn small" onClick={() => setApplyingId(null)}>
                          Cancel
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}