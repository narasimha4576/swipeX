import { useState } from "react";
import ApplicantsPanel from "./ApplicantsPanel";
import { COMP_LABEL, JOB_TYPE_LABEL, LEVEL_LABEL, salary, timeAgo } from "../jobUtils";

export default function MyPostings({ jobs, onToggle }) {
  const [openId, setOpenId] = useState(null);

  return (
    <section className="glass card">
      <h2>My postings</h2>
      <p className="muted">{jobs.length === 0 ? "No jobs posted yet." : `${jobs.length} posted`}</p>
      {jobs.map((job) => (
        <div className="posting" key={job.id}>
          <div className="item">
            <div>
              <h3>{job.title}</h3>
              <div className="muted small">
                {job.is_remote ? "Remote" : job.location} | {JOB_TYPE_LABEL[job.job_type] ?? job.job_type} |{" "}
                {LEVEL_LABEL[job.experience_level] ?? job.experience_level}
              </div>
              <div className="muted small">
                {salary(job)} | Posted {timeAgo(job.created_at)}
              </div>
              <div className="row" style={{ marginTop: "0.4rem", flexWrap: "wrap" }}>
                <span className={job.is_active ? "badge open" : "badge closed"}>
                  {job.is_active ? "Open" : "Closed"}
                </span>
                <span className={`comp ${job.competition_level}`}>
                  {COMP_LABEL[job.competition_level]}
                </span>
              </div>
            </div>
            <div className="actions">
              <button
                className="btn small primary-inline"
                onClick={() => setOpenId(openId === job.id ? null : job.id)}
              >
                {openId === job.id ? "Hide applicants" : `Applicants (${job.applicant_count})`}
              </button>
              <button className="btn small" onClick={() => onToggle(job)}>
                {job.is_active ? "Close" : "Reopen"}
              </button>
            </div>
          </div>
          {openId === job.id && <ApplicantsPanel job={job} />}
        </div>
      ))}
    </section>
  );
}