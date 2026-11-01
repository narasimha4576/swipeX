import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";

export default function MatchCard({ jobId }) {
  const [resumes, setResumes] = useState(null);
  const [resumeId, setResumeId] = useState("");
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [tips, setTips] = useState(null);
  const [tipsBusy, setTipsBusy] = useState(false);
  const [tipsError, setTipsError] = useState("");
  const [copied, setCopied] = useState("");

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
    setTips(null);
    setTipsError("");
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

  async function getTips() {
    setTipsBusy(true);
    setTipsError("");
    try {
      const { data } = await api.post(`/jobs/${jobId}/resume-tips`, null, {
        params: { resume_id: resumeId },
      });
      setTips(data);
    } catch (err) {
      setTipsError(errorMessage(err));
    } finally {
      setTipsBusy(false);
    }
  }

  async function copy(text, key) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(""), 1500);
    } catch {
      setCopied("");
    }
  }

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

          <h4 className="sheet-title">AI tips for this job</h4>
          {!tips && (
            <>
              <button className="btn small" onClick={getTips} disabled={tipsBusy}>
                {tipsBusy ? "Thinking..." : "Get AI tips for this job"}
              </button>
              <p className="muted small" style={{ marginTop: "0.6rem" }}>
                Optional. Your resume text goes to the AI after your email, phone number and links are
                removed. It may only reword what is already in your resume.
              </p>
            </>
          )}
          {tipsError && <div className="msg error">{tipsError}</div>}

          {tips && (
            <>
              {tips.summary && (
                <>
                  <div className="muted small">Suggested summary</div>
                  <p style={{ margin: "0.3rem 0" }}>{tips.summary}</p>
                  <button className="btn small" onClick={() => copy(tips.summary, "summary")}>
                    {copied === "summary" ? "Copied" : "Copy summary"}
                  </button>
                </>
              )}
              {tips.rewrites.map((r, i) => (
                <div className="rewrite" key={i}>
                  <div className="before">{r.before}</div>
                  <div style={{ marginTop: "0.4rem" }}>{r.after}</div>
                  <button className="btn small" style={{ marginTop: "0.5rem" }} onClick={() => copy(r.after, "r" + i)}>
                    {copied === "r" + i ? "Copied" : "Copy"}
                  </button>
                </div>
              ))}
              {!tips.summary && tips.rewrites.length === 0 && (
                <p className="muted small">No safe suggestions came back. Try again in a minute.</p>
              )}
              {tips.removed > 0 && (
                <p className="muted small" style={{ marginTop: "0.6rem" }}>
                  {tips.removed} suggestion{tips.removed === 1 ? " was" : "s were"} removed because{" "}
                  {tips.removed === 1 ? "it" : "they"} added facts that are not in your resume.
                </p>
              )}
              <p className="muted ai-note">AI can make mistakes. Use only what is true for you.</p>
            </>
          )}
        </>
      )}
    </div>
  );
}