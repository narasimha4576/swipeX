import { useState } from "react";
import ApplicantsPanel from "./ApplicantsPanel";
import EditJobForm from "./EditJobForm";
import { COMP_LABEL, JOB_TYPE_LABEL, LEVEL_LABEL, salary, timeAgo } from "../jobUtils";

function PostingRow({ original, onToggle }) {
  const [showApplicants, setShowApplicants] = useState(false);
  const [editing, setEditing] = useState(false);
  const [edited, setEdited] = useState(null);

  const job = edited
    ? {
        ...edited,
        is_active: original.is_active,
        applicant_count: original.applicant_count,
      }
    : original;

  return (
    <div className="posting">
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
            <span className={`comp ${job.competition_level}`}>{COMP_LABEL[job.competition_level]}</span>
          </div>
        </div>
        <div className="actions">
          <button
            className="btn small primary-inline"
            onClick={() => setShowApplicants(!showApplicants)}
          >
            {showApplicants ? "Hide applicants" : `Applicants (${job.applicant_count})`}
          </button>
          <button className="btn small" onClick={() => setEditing(!editing)}>
            {editing ? "Close editor" : "Edit"}
          </button>
          <button className="btn small" onClick={() => onToggle(original)}>
            {job.is_active ? "Close" : "Reopen"}
          </button>
        </div>
      </div>
      {editing && (
        <EditJobForm
          job={job}
          onCancel={() => setEditing(false)}
          onSaved={(saved) => {
            setEdited(saved);
            setEditing(false);
          }}
        />
      )}
      {showApplicants && <ApplicantsPanel job={job} />}
    </div>
  );
}

export default function MyPostings({ jobs, onToggle }) {
  return (
    <section className="glass card">
      <h2>My postings</h2>
      <p className="muted">{jobs.length === 0 ? "No jobs posted yet." : `${jobs.length} posted`}</p>
      {jobs.map((job) => (
        <PostingRow key={job.id} original={job} onToggle={onToggle} />
      ))}
    </section>
  );
}