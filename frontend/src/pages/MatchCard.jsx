import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";

export default function MatchCard({ jobId }) {
  const [resumes, setResumes] = useState(null);
  const [resumeId, setResumeId] = useState("");
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/resumes")
      .then(({ data }) => {
        setResumes(data);
        const pick = data.find((r) => r.is_default) ?? data[0];
        setResumeId(pick ? String(pick.id) : "");
      })
      .catch(() => setResumes([]));
  }, []);

  useEffect(() => {
    if (!resumeId) return;
    let cancelled = false;
    setInfo(null);
    setError("");
    api
      .get(`/jobs/${jobId}/match`, { params: { resume_id: resumeId } })
      .then(({ data }) => {
        if (!cancelled) setInfo(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [jobId, resumeId]);

  if (resumes === null) return null;

  if (resumes.length === 0) {
    return (
      <div className="match-card">
        <h4 className="sheet-title" style={{ marginTop: 0 }}>
          Resume match
        </h4>
        <p className="muted small">
          Upload a resume to see how well you match this job.{" "}
          <Link className="link" to="/profile">
            Go to Profile
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="match-card">
      <h4 className="sheet-title" style={{ marginTop: 0 }}>
        Resume match
      </h4>

      {resumes.length > 1 && (
        <select value={resumeId} onChange={(e) => setResumeId(e.target.value)} style={{ marginBottom: "0.8rem" }}>
          {resumes.map((r) => (
            <option key={r.id} value={r.id}>
              {r.version_name}
              {r.is_default ? " (default)" : ""}
            </option>
          ))}
        </select>
      )}

      {!info && !error && <p className="muted small">Comparing your resume with this job...</p>}
      {error && <div className="msg error">{error}</div>}

      {info && (
        <>
          <div className="score-row">
            <div className="score-big">{info.score}%</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700 }}>{info.label}</div>
              <div className="meter">
                <div style={{ width: info.score + "%" }} />
              </div>
              <div className="muted small">Wording similarity {info.text_match_percent}%</div>
            </div>
          </div>

          {info.matched_skills.length > 0 && (
            <>
              <div className="muted small" style={{ marginTop: "0.8rem" }}>
                Skills you have
              </div>
              <div className="chips">
                {info.matched_skills.map((s) => (
                  <span className="chip good" key={s}>
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}
          {info.missing_skills.length > 0 && (
            <>
              <div className="muted small" style={{ marginTop: "0.8rem" }}>
                Not found in your resume
              </div>
              <div className="chips">
                {info.missing_skills.map((s) => (
                  <span className="chip miss" key={s}>
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}
          <ul className="tips-list">
            {info.tips.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
          <p className="muted small">An estimate to help you decide. Real company systems score differently.</p>
        </>
      )}
    </div>
  );
}