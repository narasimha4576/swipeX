import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const TYPE_LABEL = { mnc: "MNC", startup: "Startup", new_startup: "New startup" };
const JOB_TYPE_LABEL = { full_time: "Full-time", internship: "Internship" };
const LEVEL_LABEL = { fresher: "Fresher", junior: "Junior", mid: "Mid-level", senior: "Senior" };
const PAGE_SIZE = 9;

function timeAgo(iso) {
  const then = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  const hours = Math.floor((Date.now() - then.getTime()) / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "1 day ago" : `${days} days ago`;
}

function salary(job) {
  if (job.salary_min_lpa == null || job.salary_max_lpa == null) return "Not disclosed";
  return `${job.salary_min_lpa} - ${job.salary_max_lpa} LPA`;
}

export default function Jobs() {
  const [data, setData] = useState({ items: [], total: 0 });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .get("/jobs", { params: { page, page_size: PAGE_SIZE } })
      .then(({ data }) => setData(data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [page]);

  const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Jobs</h2>
          <p className="muted">{data.total} openings, newest first</p>
        </div>
      </div>

      {error && <div className="msg error">{error}</div>}
      {loading && <p className="muted">Loading jobs...</p>}

      <div className="jobs-grid">
        {data.items.map((job) => (
          <article className="glass job-card" key={job.id}>
            <div className="row between">
              <div>
                <h3>{job.title}</h3>
                <div className="muted">{job.company.name}</div>
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
              <span>{job.applicant_count} applicants</span>
            </div>

            <details>
              <summary>Details</summary>
              <p className="muted">{job.description}</p>
            </details>
          </article>
        ))}
      </div>

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
    </section>
  );
}