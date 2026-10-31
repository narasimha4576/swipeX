import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import { useAuth } from "../auth";
import CompanyLink from "./CompanyLink";
import SafetyCard from "./SafetyCard";
import {
  COMP_LABEL,
  isThirdParty,
  sourceBadge,
  JOB_TYPE_LABEL,
  LEVEL_LABEL,
  TYPE_LABEL,
  salary,
  timeAgo,
} from "../jobUtils";

const STATUS_LABEL = {
  saved: "Saved",
  applied: "Applied",
  shortlisted: "Shortlisted",
  interview: "Interview",
  rejected: "Rejected",
};

export default function JobDetail({ jobId, embedded = false }) {
  const params = useParams();
  const id = jobId ?? params.id;
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSeeker = user.role === "job_seeker";

  const [job, setJob] = useState(null);
  const [mine, setMine] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [resumeId, setResumeId] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  function goBack() {
    if (window.history.length > 1) navigate(-1);
    else navigate("/jobs");
  }

  async function loadMine() {
    const { data } = await api.get(`/applications/job/${id}`);
    setMine(data);
    return data;
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const { data } = await api.get(`/jobs/${id}`);
        if (cancelled) return;
        setJob(data);
        if (isSeeker) {
          const [status, list] = await Promise.all([
            api.get(`/applications/job/${id}`),
            api.get("/resumes"),
          ]);
          if (cancelled) return;
          setMine(status.data);
          setResumes(list.data);
          const pick = list.data.find((r) => r.is_default) ?? list.data[0];
          setResumeId(pick ? String(pick.id) : "");
        }
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id, isSeeker]);

  async function run(task) {
    setBusy(true);
    setError("");
    setOk("");
    try {
      await task();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function ensureSaved() {
    if (mine) return mine;
    await api.post("/swipes", { job_id: job.id, direction: "right" });
    return loadMine();
  }

  function save() {
    run(async () => {
      await ensureSaved();
      setOk("Saved. You can find it in your Applications tab.");
    });
  }

  function applyNative() {
    run(async () => {
      await api.post("/applications/apply", { job_id: job.id, resume_id: Number(resumeId) });
      await loadMine();
      setOk(`Your application was sent to ${job.company.name}.`);
    });
  }

  function applyOnCompanySite() {
    if (!job.apply_url) {
      setError("This job has no apply link");
      return;
    }
    window.open(job.apply_url, "_blank", "noopener,noreferrer");
    run(async () => {
      await ensureSaved();
      setWaiting(true);
    });
  }

  function markApplied() {
    run(async () => {
      const current = await ensureSaved();
      await api.post(`/applications/${current.application_id}/mark-applied`);
      await loadMine();
      setWaiting(false);
      setOk("Marked as applied. Track it in your Applications tab.");
    });
  }

  if (!job) {
    return (
      <div className={"detail-page" + (embedded ? " embedded-detail" : "")}>
        <button className="btn small" style={{ alignSelf: "flex-start" }} onClick={goBack}>
          Back
        </button>
        {error ? <div className="msg error">{error}</div> : <p className="muted">Loading job...</p>}
      </div>
    );
  }

  const status = mine?.status;
  const official = job.source !== "native";
  const applied = Boolean(status) && status !== "saved";

  return (
    <div className={"detail-page" + (embedded ? " embedded-detail" : "")}>
      <button className="btn small" style={{ alignSelf: "flex-start" }} onClick={goBack}>
        Back
      </button>

      <div className="detail">
        <article className="glass card detail-main">
          <div className="job-top">
            <div className="logo">{job.company.name.charAt(0)}</div>
            <div className="job-title">
              <CompanyLink company={job.company} />
              <div className="row" style={{ marginTop: "0.3rem", flexWrap: "wrap" }}>
                <span className={`badge ${job.company.company_type}`}>
                  {TYPE_LABEL[job.company.company_type] ?? job.company.company_type}
                </span>
                {official && <span className="badge mnc">{sourceBadge(job.source)}</span>}
              </div>
            </div>
          </div>

          <h1 className="detail-title">{job.title}</h1>

          <div className="meta">
            <span>{job.is_remote ? "Remote" : job.location}</span>
            <span>{JOB_TYPE_LABEL[job.job_type] ?? job.job_type}</span>
            <span>{LEVEL_LABEL[job.experience_level] ?? job.experience_level}</span>
            <span>Posted {timeAgo(job.created_at)}</span>
          </div>

          <div className="salary" style={{ margin: "0.8rem 0" }}>
            {salary(job)}
          </div>

          <div className="chips">
            {job.skills.map((s) => (
              <span className="chip" key={s}>
                {s}
              </span>
            ))}
          </div>

          <div className="stats" style={{ marginTop: "1rem" }}>
            <span className="stat">
              {job.source === "native" ? `${job.applicant_count} applicants` : "Applications on company site"}
            </span>
            <span className={`comp ${job.competition_level}`}>{COMP_LABEL[job.competition_level]}</span>
          </div>

          {isThirdParty(job.source) && (<div className="warn-note" style={{ marginTop: "1rem" }}>Third-party listing. SwipeX has not checked this company or posting. Apply at your own risk.</div>)}

          <SafetyCard jobId={job.id} />

          <h4 className="sheet-title">About this role</h4>
          <div className="description">{job.description}</div>
        </article>

        <aside className="glass card detail-side">
          <h3>Apply</h3>
          {error && <div className="msg error">{error}</div>}
          {ok && <div className="msg ok">{ok}</div>}

          {!isSeeker && (
            <p className="muted small">
              Only job seekers can apply. You are viewing this job as a {user.role.replace("_", " ")}.
            </p>
          )}

          {isSeeker && (
            <>
              {status && (
                <p>
                  <span className={`badge ${status}`}>{STATUS_LABEL[status]}</span>
                </p>
              )}

              {applied && (
                <>
                  <p className="muted small">
                    {official
                      ? "You applied on the company site."
                      : "Your application was sent with your profile and resume."}{" "}
                    Track every step in your Applications tab.
                  </p>
                  <Link className="btn small" to="/applications">
                    Open applications
                  </Link>
                </>
              )}

              {!applied && official && (
                <>
                  <Link className="btn primary" to={"/jobs/" + job.id + "/apply"}>Review and autofill</Link>
                  <button className="btn" style={{ width: "100%" }} onClick={applyOnCompanySite} disabled={busy}>
                    Apply on company site
                  </button>
                  {waiting && (
                    <div className="apply-panel">
                      <p className="muted small">
                        Finish the form on the company page that just opened, then confirm here.
                      </p>
                      <div className="actions">
                        <button className="btn small primary-inline" onClick={markApplied} disabled={busy}>
                          Yes, I applied
                        </button>
                        <button className="btn small" onClick={() => setWaiting(false)}>
                          Not yet
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}

              {!applied && !official && (
                <>
                  {resumes.length === 0 ? (
                    <p className="muted small">
                      Upload a resume to apply.{" "}
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
                      <button
                        className="btn primary"
                        onClick={applyNative}
                        disabled={busy || !resumeId}
                      >
                        Apply now
                      </button>
                    </>
                  )}
                </>
              )}

              {!status && (
                <button
                  className="btn"
                  style={{ width: "100%", marginTop: "0.8rem" }}
                  onClick={save}
                  disabled={busy}
                >
                  Save for later
                </button>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}