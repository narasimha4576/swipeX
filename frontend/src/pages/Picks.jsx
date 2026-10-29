import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import CompanyLink from "./CompanyLink";
import { LEVEL_LABEL, TYPE_LABEL, logoColor, salary, timeAgo } from "../jobUtils";

function PickCard({ job, note, children }) {
  return (
    <article className="glass job-card">
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
        <span>{LEVEL_LABEL[job.experience_level] ?? job.experience_level}</span>
      </div>
      <div className="salary">{salary(job)}</div>
      {note && <div className="muted small">{note}</div>}
      <div className="actions">{children}</div>
    </article>
  );
}

export default function Picks() {
  const [tab, setTab] = useState("liked");
  const [liked, setLiked] = useState([]);
  const [skipped, setSkipped] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  async function load() {
    try {
      const [apps, skips] = await Promise.all([api.get("/applications"), api.get("/swipes/skipped")]);
      setLiked(apps.data.filter((a) => a.status === "saved"));
      setSkipped(skips.data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function run(task, message) {
    setError("");
    setOk("");
    try {
      await task();
      if (message) setOk(message);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const likeIt = (item) =>
    run(() => api.post("/swipes", { job_id: item.job.id, direction: "right" }), "Moved to Liked");
  const backToDiscover = (item) =>
    run(() => api.delete(`/swipes/${item.job.id}`), "It will show up in Discover again");
  const removeLiked = (app) => run(() => api.delete(`/applications/${app.id}`), "Moved to Skipped");

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Picks</h2>
          <p className="muted">Jobs you liked and jobs you skipped.</p>
        </div>
      </div>

      <div className="filter-bar">
        <button className={tab === "liked" ? "fchip on" : "fchip"} onClick={() => setTab("liked")}>
          Liked ({liked.length})
        </button>
        <button className={tab === "skipped" ? "fchip on" : "fchip"} onClick={() => setTab("skipped")}>
          Skipped ({skipped.length})
        </button>
      </div>

      {error && <div className="msg error">{error}</div>}
      {ok && <div className="msg ok">{ok}</div>}
      {loading && <p className="muted">Loading...</p>}

      {tab === "skipped" && !loading && (
        <p className="muted small">
          Skipped jobs are kept for 15 days and then cleared automatically. After that, a job can
          show up in Discover again if it is still open.
        </p>
      )}

      {!loading && tab === "liked" && liked.length === 0 && (
        <div className="glass card empty">
          <h3>No liked jobs yet</h3>
          <p className="muted">Swipe right in Discover, or tap Save on a job page.</p>
        </div>
      )}
      {!loading && tab === "skipped" && skipped.length === 0 && (
        <div className="glass card empty">
          <h3>No skipped jobs</h3>
          <p className="muted">Jobs you skip will wait here for 15 days.</p>
        </div>
      )}

      <div className="jobs-grid">
        {tab === "liked" &&
          liked.map((a) => (
            <PickCard key={a.id} job={a.job} note={`Liked ${timeAgo(a.created_at)}`}>
              <Link className="btn small primary-inline" to={"/jobs/" + a.job.id}>
                Apply or view
              </Link>
              <button className="btn small" onClick={() => removeLiked(a)}>
                Remove
              </button>
            </PickCard>
          ))}
        {tab === "skipped" &&
          skipped.map((item) => (
            <PickCard
              key={item.job.id}
              job={item.job}
              note={`Skipped ${timeAgo(item.skipped_at)}, cleared in ${item.days_left} days`}
            >
              <button className="btn small primary-inline" onClick={() => likeIt(item)}>
                Like it
              </button>
              <button className="btn small" onClick={() => backToDiscover(item)}>
                Back to Discover
              </button>
              <Link className="btn small" to={"/jobs/" + item.job.id}>
                Details
              </Link>
            </PickCard>
          ))}
      </div>
    </section>
  );
}