import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth";
import CompanyLink from "./CompanyLink";
import { JOB_TYPE_LABEL, logoColor, sourceBadge, timeAgo } from "../jobUtils";

function MiniJob({ job }) {
  return (
    <div className="mini-job">
      <div className="logo" style={{ background: logoColor(job.company.name) }}>
        {job.company.name.charAt(0)}
      </div>
      <div className="job-title">
        <Link className="title-link" to={"/jobs/" + job.id}>
          <strong>{job.title}</strong>
        </Link>
        <div className="muted small">
          <CompanyLink company={job.company} />
          {" | "}
          {job.is_remote ? "Remote" : job.location || "Location not listed"}
        </div>
        <div className="muted small">
          {JOB_TYPE_LABEL[job.job_type] ?? job.job_type} | {sourceBadge(job.source)} | {timeAgo(job.created_at)}
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [profile, setProfile] = useState(null);
  const [forYou, setForYou] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [found, setFound] = useState({ jobs: [], total: 0, companies: [] });
  const [loading, setLoading] = useState(false);
  const text = q.trim();
  const searching = text.length >= 2;

  useEffect(() => {
    api.get("/profile/me").then(({ data }) => setProfile(data)).catch(() => {});
    api.get("/jobs-for-you").then(({ data }) => setForYou(data)).catch(() => {});
    api
      .get("/explore/featured")
      .then(({ data }) => setFeatured(data.slice(0, 6)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (text.length < 2) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(() => {
      Promise.all([
        api.get("/jobs", { params: { q: text, page_size: 6, verified_only: false } }),
        api.get("/explore/search", { params: { q: text } }),
      ])
        .then(([jobs, companies]) => {
          if (!cancelled) {
            setFound({
              jobs: jobs.data.items,
              total: jobs.data.total,
              companies: companies.data.companies.slice(0, 4),
            });
          }
        })
        .catch(() => {})
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [text]);

  function submit(e) {
    e.preventDefault();
    if (text) navigate("/jobs?q=" + encodeURIComponent(text));
  }

  const strength = profile
    ? (profile.headline ? 25 : 0) +
      (profile.location ? 25 : 0) +
      (profile.bio ? 25 : 0) +
      (profile.skills && profile.skills.length >= 3 ? 25 : 0)
    : 0;

  return (
    <div className="home">
      <aside className="home-side left">
        <div className="glass card profile-mini">
          <div className="avatar big">{user.full_name.trim().charAt(0).toUpperCase()}</div>
          <h3>{user.full_name}</h3>
          <p className="muted small">{profile?.headline || "Add a headline to your profile"}</p>
          <div className="meter">
            <div style={{ width: strength + "%" }} />
          </div>
          <p className="muted small">Profile strength {strength}%</p>
          <Link className="btn small" to="/profile">
            Edit profile
          </Link>
        </div>
        <div className="glass card">
          <h4 className="sheet-title" style={{ marginTop: 0 }}>
            Shortcuts
          </h4>
          <div className="home-links">
            <Link to="/picks">Liked and skipped jobs</Link>
            <Link to="/applications">My applications</Link>
            <Link to="/discover">Swipe jobs</Link>
          </div>
        </div>
      </aside>

      <div className="home-main">
        <form className="glass card" onSubmit={submit}>
          <h2>Find your next job</h2>
          <div className="search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search jobs, skills or companies"
            />
          </div>
        </form>

        {searching ? (
          <>
            <section className="glass card">
              <h2>Jobs</h2>
              {loading && <p className="muted">Searching...</p>}
              {!loading && found.jobs.length === 0 && <p className="muted">No jobs found for "{text}".</p>}
              {found.jobs.map((job) => (
                <MiniJob key={job.id} job={job} />
              ))}
              {found.total > 0 && (
                <Link className="btn small" to={"/jobs?q=" + encodeURIComponent(text)}>
                  See all {found.total} jobs
                </Link>
              )}
            </section>

            <section className="glass card">
              <h2>Companies</h2>
              {found.companies.map((c) => (
                <div className="job-row" key={c.id}>
                  <div>
                    <Link className="title-link" to={"/companies/" + c.id}>
                      <strong>{c.name}</strong>
                    </Link>
                    <div className="muted small">
                      {c.location || "Location not listed"} | {c.open_jobs} open jobs
                    </div>
                  </div>
                  <span className={"badge " + c.verification_status}>{c.verification_status}</span>
                </div>
              ))}
              <Link
                className="web-cta"
                style={{ marginTop: "0.8rem" }}
                to={"/companies/web?name=" + encodeURIComponent(text)}
              >
                <strong>Search the web for "{text}"</strong>
                <div className="muted small">Jobs, photos, videos, news and web results for any company</div>
              </Link>
            </section>
          </>
        ) : (
          <section className="glass card">
            <h2>Jobs for you</h2>
            <p className="muted small">Ranked by how well they match your skills, then by newest.</p>
            {forYou.length === 0 && <p className="muted">Jobs will appear here as soon as they are imported.</p>}
            {forYou.map((job) => (
              <MiniJob key={job.id} job={job} />
            ))}
            <Link className="btn small" to="/jobs">
              Browse all jobs
            </Link>
          </section>
        )}
      </div>

      <aside className="home-side right">
        <div className="glass card">
          <h4 className="sheet-title" style={{ marginTop: 0 }}>
            Companies hiring
          </h4>
          {featured.map((c) => (
            <div className="job-row" key={c.id}>
              <Link className="title-link" to={"/companies/" + c.id}>
                {c.name}
              </Link>
              <span className="muted small">{c.open_jobs} jobs</span>
            </div>
          ))}
        </div>
        <div className="glass card">
          <h4 className="sheet-title" style={{ marginTop: 0 }}>
            Tip
          </h4>
          <p className="muted small">
            Add skills to your profile. Jobs for you are ranked by the skills you list, and Review and
            autofill fills company forms from your saved details.
          </p>
        </div>
      </aside>
    </div>
  );
}