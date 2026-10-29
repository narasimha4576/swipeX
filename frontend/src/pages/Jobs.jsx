import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import CompanyLink from "./CompanyLink";
import OtherPortals from "./OtherPortals";
import {
  COMP_LABEL,
  JOB_TYPE_LABEL,
  LEVEL_LABEL,
  TYPE_LABEL,
  logoColor,
  salary,
  timeAgo,
} from "../jobUtils";

const PAGE_SIZE = 9;
const REFRESH_MS = 60000;

const EMPTY = {
  q: "",
  verified_only: true,
  company_type: "",
  job_type: "",
  experience_level: "",
  remote: false,
  location: "",
  skill: "",
  min_salary: "",
  max_age_days: "",
  fresher_friendly: false,
  low_competition: false,
  sort: "newest",
};

const QUICK = [
  ["MNC", "company_type", "mnc"],
  ["Startup", "company_type", "startup"],
  ["New startup", "company_type", "new_startup"],
  ["Remote", "remote", true],
  ["Fresher-friendly", "fresher_friendly", true],
  ["Low competition", "low_competition", true],
  ["Last 7 days", "max_age_days", 7],
  ["Internships", "job_type", "internship"],
  ["Apprenticeships", "job_type", "apprenticeship"],
];

function toParams(f, page) {
  const p = { page, page_size: PAGE_SIZE, sort: f.sort };
  if (f.q.trim()) p.q = f.q.trim();
  ["company_type", "job_type", "experience_level", "location", "skill"].forEach((k) => {
    if (typeof f[k] === "string" && f[k].trim()) p[k] = f[k].trim();
  });
  if (!f.verified_only) p.verified_only = false;
  if (f.remote) p.remote = true;
  if (f.fresher_friendly) p.fresher_friendly = true;
  if (f.low_competition) p.low_competition = true;
  if (f.min_salary !== "") p.min_salary = Number(f.min_salary);
  if (f.max_age_days) p.max_age_days = f.max_age_days;
  return p;
}

function clock(date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Jobs() {
  const [filters, setFilters] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const [showPanel, setShowPanel] = useState(false);
  const [data, setData] = useState({ items: [], total: 0 });
  const [fresh, setFresh] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const latest = useRef({ filters, page, data });

  useEffect(() => {
    latest.current = { filters, page, data };
  });

  function update(patch) {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  }

  function reset() {
    setFilters(EMPTY);
    setPage(1);
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(() => {
      api
        .get("/jobs", { params: toParams(filters, page) })
        .then(({ data }) => {
          if (!cancelled) {
            setData(data);
            setFresh(null);
            setUpdatedAt(new Date());
            setError("");
          }
        })
        .catch((err) => {
          if (!cancelled) setError(errorMessage(err));
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [filters, page]);

  // Every minute, quietly check for new jobs and offer a refresh banner.
  useEffect(() => {
    const timer = setInterval(async () => {
      if (document.hidden) return;
      const current = latest.current;
      try {
        const { data: next } = await api.get("/jobs", {
          params: toParams(current.filters, current.page),
        });
        const ids = (list) => list.items.map((j) => j.id).join(",");
        if (next.total !== current.data.total || ids(next) !== ids(current.data)) {
          setFresh(next);
        } else {
          setUpdatedAt(new Date());
        }
      } catch {
        // A failed background check is ignored. The next one tries again.
      }
    }, REFRESH_MS);
    return () => clearInterval(timer);
  }, []);

  const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const panelCount =
    [filters.location, filters.skill, filters.min_salary, filters.experience_level].filter(
      (v) => String(v).trim() !== ""
    ).length + (filters.sort !== "newest" ? 1 : 0);
  const anyFilter =
    JSON.stringify({ ...filters, sort: "newest" }) !== JSON.stringify({ ...EMPTY });

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Jobs</h2>
          <p className="muted">
            {data.total} openings
            {updatedAt ? ` | Updated ${clock(updatedAt)}, checks every minute` : ""}
          </p>
        </div>
      </div>

      <div className="search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <input
          value={filters.q}
          onChange={(e) => update({ q: e.target.value })}
          placeholder="Search jobs, companies or skills"
        />
      </div>

      <div className="filter-bar">
        <button
          className={showPanel ? "fchip on" : "fchip"}
          onClick={() => setShowPanel(!showPanel)}
        >
          Filters{panelCount > 0 ? ` (${panelCount})` : ""}
        </button>
        <button className={filters.verified_only ? "fchip on" : "fchip"} onClick={() => update({ verified_only: !filters.verified_only })}>Verified only</button>
        {QUICK.map(([label, key, value]) => (
          <button
            key={label}
            className={filters[key] === value ? "fchip on" : "fchip"}
            onClick={() => update({ [key]: filters[key] === value ? EMPTY[key] : value })}
          >
            {label}
          </button>
        ))}
      </div>

      {showPanel && (
        <div className="glass card panel">
          <div className="grid2">
            <label className="field">
              <span>Location</span>
              <input
                value={filters.location}
                onChange={(e) => update({ location: e.target.value })}
                placeholder="e.g. Bengaluru"
              />
            </label>
            <label className="field">
              <span>Skill</span>
              <input
                value={filters.skill}
                onChange={(e) => update({ skill: e.target.value })}
                placeholder="e.g. Python"
              />
            </label>
          </div>
          <div className="grid2">
            <label className="field">
              <span>Minimum salary (LPA)</span>
              <input
                type="number"
                min="0"
                value={filters.min_salary}
                onChange={(e) => update({ min_salary: e.target.value })}
                placeholder="e.g. 8"
              />
            </label>
            <label className="field">
              <span>Experience level</span>
              <select
                value={filters.experience_level}
                onChange={(e) => update({ experience_level: e.target.value })}
              >
                <option value="">Any</option>
                <option value="fresher">Fresher</option>
                <option value="junior">Junior</option>
                <option value="mid">Mid-level</option>
                <option value="senior">Senior</option>
              </select>
            </label>
          </div>
          <label className="field">
            <span>Sort by</span>
            <select value={filters.sort} onChange={(e) => update({ sort: e.target.value })}>
              <option value="newest">Newest first</option>
              <option value="salary">Highest salary</option>
              <option value="competition">Fewest applicants</option>
            </select>
          </label>
          <button className="btn small" onClick={reset}>
            Reset all filters
          </button>
        </div>
      )}

      {fresh && (
        <button
          className="update-banner"
          onClick={() => {
            setData(fresh);
            setFresh(null);
            setUpdatedAt(new Date());
          }}
        >
          New jobs are available. Tap to show them
        </button>
      )}

      {error && <div className="msg error">{error}</div>}
      {loading && <p className="muted">Loading jobs...</p>}

      {!loading && data.items.length === 0 && (
        <div className="glass card empty">
          <h3>No jobs match</h3>
          <p className="muted">Try removing a filter or searching for something else.</p>
          {anyFilter && (
            <button className="btn small" onClick={reset}>
              Reset all filters
            </button>
          )}
        </div>
      )}

      <div className="jobs-grid">
        {data.items.map((job) => (
          <article className="glass job-card" key={job.id}>
            <div className="job-top">
              <div className="logo" style={{ background: logoColor(job.company.name) }}>
                {job.company.name.charAt(0)}
              </div>
              <div className="job-title">
                <h3>
                  <Link className="title-link" to={"/jobs/" + job.id}>
                    {job.title}
                  </Link>
                </h3>
                <CompanyLink company={job.company} />
              </div>
              <span className={`badge ${job.company.company_type}`}>
                {TYPE_LABEL[job.company.company_type] ?? job.company.company_type}
              </span>
            </div>

            <div className="meta">
              <span>{job.is_remote ? "Remote" : job.location}</span>
              <span>{JOB_TYPE_LABEL[job.job_type] ?? job.job_type}</span>
              <span>{LEVEL_LABEL[job.experience_level] ?? job.experience_level}</span>
            </div>

            {job.company.verification_status !== "verified" && (<div className="warn-note">Unverified company. Check the safety details before applying.</div>)}
            <div className="salary">{salary(job)}</div>

            <div className="chips">
              {job.skills.slice(0, 5).map((s) => (
                <span className="chip" key={s}>
                  {s}
                </span>
              ))}
            </div>

            <div className="row between foot muted small">
              <span>Posted {timeAgo(job.created_at)}</span>
              <span>
                {job.source === "native" ? `${job.applicant_count} applicants` : job.source === "adzuna" ? "Aggregated listing" : "Official listing"}
              </span>
            </div>
            <div className={`comp ${job.competition_level}`}>{COMP_LABEL[job.competition_level]}</div>

            <Link className="btn small details-link" to={"/jobs/" + job.id}>
              View details
            </Link>
          </article>
        ))}
      </div>

      <OtherPortals query={filters.q} location={filters.location} />

      {data.total > 0 && (
        <div className="pager">
          <button className="btn small" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span className="muted small">
            Page {page} of {pages}
          </span>
          <button className="btn small" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </div>
      )}
    </section>
  );
}