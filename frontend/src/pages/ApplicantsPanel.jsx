import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { timeAgo } from "../jobUtils";

const FILTERS = [
  ["all", "All"],
  ["applied", "Applied"],
  ["shortlisted", "Shortlisted"],
  ["interview", "Interview"],
  ["rejected", "Rejected"],
];
const STATUS_LABEL = {
  applied: "Applied",
  shortlisted: "Shortlisted",
  interview: "Interview",
  rejected: "Rejected",
};
const ACTIONS = [
  ["shortlisted", "Shortlist"],
  ["interview", "Interview"],
  ["rejected", "Reject"],
];

export default function ApplicantsPanel({ job }) {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all");
  const [openId, setOpenId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    try {
      const { data } = await api.get(`/recruiter/jobs/${job.id}/applicants`);
      setItems(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [job.id]);

  async function setStatus(a, status) {
    setError("");
    try {
      await api.patch(`/recruiter/applications/${a.application_id}/status`, { status });
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function viewResume(a) {
    setError("");
    const win = window.open("", "_blank");
    if (!win) {
      setError("Please allow pop-ups to view the file");
      return;
    }
    try {
      const { data } = await api.get(`/recruiter/applications/${a.application_id}/resume`, {
        responseType: "blob",
      });
      win.location.href = URL.createObjectURL(data);
    } catch {
      win.close();
      setError("Could not open the resume");
    }
  }

  const counts = items.reduce((acc, a) => {
    acc[a.status] = (acc[a.status] ?? 0) + 1;
    return acc;
  }, {});
  const shown = filter === "all" ? items : items.filter((a) => a.status === filter);

  return (
    <div className="applicants">
      <div className="filter-bar">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            className={filter === key ? "fchip on" : "fchip"}
            onClick={() => setFilter(key)}
          >
            {label} ({key === "all" ? items.length : counts[key] ?? 0})
          </button>
        ))}
      </div>

      {error && <div className="msg error">{error}</div>}
      {loading && <p className="muted">Loading applicants...</p>}
      {!loading && shown.length === 0 && <p className="muted">No applicants here yet.</p>}

      {shown.map((a) => (
        <div className="applicant" key={a.application_id}>
          <div className="row between">
            <div>
              <h3>{a.full_name}</h3>
              <div className="muted small">{a.headline || "No headline added"}</div>
              <div className="muted small">
                {[a.location, `${a.experience_years} yrs experience`].filter(Boolean).join("  |  ")}
              </div>
            </div>
            <span className={`badge ${a.status}`}>{STATUS_LABEL[a.status]}</span>
          </div>

          <div className="chips">
            {a.skills.map((s) => (
              <span className="chip" key={s}>
                {s}
              </span>
            ))}
          </div>

          <div className="muted small">
            {a.status === "applied" ? "Applied " : "Updated "}
            {timeAgo(a.updated_at)}
            {a.resume_name ? `  |  Resume: ${a.resume_name}` : ""}
          </div>

          <div className="actions">
            <button className="btn small" disabled={!a.resume_name} onClick={() => viewResume(a)}>
              Resume
            </button>
            <button
              className="btn small"
              onClick={() => setOpenId(openId === a.application_id ? null : a.application_id)}
            >
              {openId === a.application_id ? "Hide details" : "Details"}
            </button>
            {ACTIONS.map(([status, label]) => (
              <button
                key={status}
                className={a.status === status ? "btn small on" : "btn small"}
                disabled={a.status === status}
                onClick={() => setStatus(a, status)}
              >
                {label}
              </button>
            ))}
            {a.status !== "applied" && (
              <button className="btn small" onClick={() => setStatus(a, "applied")}>
                Reset
              </button>
            )}
          </div>

          {openId === a.application_id && (
            <div className="applicant-details">
              <div>
                <span className="muted small">Email</span>
                <div>{a.email}</div>
              </div>
              {a.bio && (
                <div>
                  <span className="muted small">About</span>
                  <div>{a.bio}</div>
                </div>
              )}
              <div>
                <span className="muted small">Experience</span>
                {a.experiences.length === 0 && <div className="muted">None added</div>}
                {a.experiences.map((x) => (
                  <div key={x.id}>
                    {x.title} at {x.company} ({x.start_year} - {x.end_year ?? "Present"})
                  </div>
                ))}
              </div>
              <div>
                <span className="muted small">Portfolio</span>
                {a.portfolio.length === 0 && <div className="muted">None added</div>}
                {a.portfolio.map((p) => (
                  <div key={p.id}>
                    <a className="link" href={p.url} target="_blank" rel="noreferrer">
                      {p.title}
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}