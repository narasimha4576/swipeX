import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import { detectExtension, sendAutofill } from "../extension";

function yesNo(value) {
  return value ? "Yes" : "No";
}

function ctc(value) {
  return value === null || value === undefined ? null : `${value} LPA`;
}

export default function ApplyReview() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [payload, setPayload] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [resumeId, setResumeId] = useState("");
  const [coverLetter, setCoverLetter] = useState("");
  const [extension, setExtension] = useState(null);
  const [stage, setStage] = useState("review");
  const [busy, setBusy] = useState(false);
  const [useAi, setUseAi] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.get(`/autofill/payload/${id}`), api.get("/resumes")])
      .then(([p, r]) => {
        if (cancelled) return;
        setPayload(p.data);
        setResumes(r.data);
        setResumeId(p.data.resume ? String(p.data.resume.id) : "");
        setCoverLetter(p.data.applicant.cover_letter ?? "");
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    detectExtension().then((found) => {
      if (!cancelled) setExtension(found);
    });
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function ensureSaved() {
    const { data } = await api.get(`/applications/job/${id}`);
    if (data) return data;
    await api.post("/swipes", { job_id: Number(id), direction: "right" });
    const again = await api.get(`/applications/job/${id}`);
    return again.data;
  }

  async function startAutofill() {
    setBusy(true);
    setError("");
    setOk("");
    try {
      const { data } = await api.get(`/autofill/payload/${id}`, {
        params: { include_resume: true, ...(resumeId ? { resume_id: resumeId } : {}) },
      });
      data.applicant.cover_letter = coverLetter.trim() || null;
      if (useAi) {
        const issued = await api.post("/autofill/token");
        data.ai = { token: issued.data.token, api: api.defaults.baseURL };
      }
      const accepted = await sendAutofill(data);
      if (!accepted) {
        setExtension(false);
        setError(
          "The SwipeX Autofill extension did not respond. Install it, or open the company page without autofill."
        );
        return;
      }
      await ensureSaved();
      setStage("waiting");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function openWithoutAutofill() {
    window.open(payload.job.apply_url, "_blank", "noopener,noreferrer");
    setBusy(true);
    setError("");
    try {
      await ensureSaved();
      setStage("waiting");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function markApplied() {
    setBusy(true);
    setError("");
    try {
      const current = await ensureSaved();
      await api.post(`/applications/${current.application_id}/mark-applied`);
      setOk("Marked as applied. You can track it in your Applications tab.");
      setStage("done");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!payload) {
    return (
      <div className="detail-page">
        <button className="btn small" style={{ alignSelf: "flex-start" }} onClick={() => navigate(-1)}>
          Back
        </button>
        {error ? <div className="msg error">{error}</div> : <p className="muted">Preparing your application...</p>}
      </div>
    );
  }

  const a = payload.applicant;
  const rows = [
    ["Name", a.full_name],
    ["Email", a.email],
    ["Phone", a.phone],
    ["Location", a.location],
    ["LinkedIn", a.linkedin_url],
    ["GitHub", a.github_url],
    ["Portfolio", a.portfolio_url],
    ["College", a.college],
    ["Degree", [a.degree, a.discipline].filter(Boolean).join(" in ") || null],
    ["Graduation year", a.graduation_year],
    ["Work authorization", a.authorized_countries],
    ["Needs sponsorship", yesNo(a.requires_sponsorship)],
    ["Willing to relocate", yesNo(a.willing_to_relocate)],
    ["Notice period", a.notice_period_days === null ? null : `${a.notice_period_days} days`],
    ["Current CTC", ctc(a.current_ctc_lpa)],
    ["Expected CTC", ctc(a.expected_ctc_lpa)],
    ["How did you hear about us", a.how_did_you_hear],
  ];

  return (
    <div className="detail-page">
      <button className="btn small" style={{ alignSelf: "flex-start" }} onClick={() => navigate(-1)}>
        Back
      </button>

      <section className="glass card">
        <h2>Review and autofill</h2>
        <p className="muted">
          {payload.job.title} at {payload.job.company}
        </p>

        {!payload.ready && (
          <div className="msg error">
            Add your {payload.missing.join(" and ")} first.{" "}
            <Link className="link" to="/profile">
              Go to Profile
            </Link>
          </div>
        )}
        {error && <div className="msg error">{error}</div>}
        {ok && <div className="msg ok">{ok}</div>}

        <h4 className="sheet-title">What will be filled in</h4>
        {rows.map(([label, value]) => (
          <div className="review-row" key={label}>
            <span>{label}</span>
            {value === null || value === undefined || value === "" ? (
              <span className="unset">Not set</span>
            ) : (
              <span>{value}</span>
            )}
          </div>
        ))}
        <p className="never">
          Edit these in your Profile. SwipeX never answers diversity or demographic questions, never
          fills passwords, and never presses Submit for you.
        </p>

        <h4 className="sheet-title">Resume</h4>
        {resumes.length === 0 ? (
          <p className="muted small">
            No resume yet.{" "}
            <Link className="link" to="/profile">
              Upload one
            </Link>
          </p>
        ) : (
          <select value={resumeId} onChange={(e) => setResumeId(e.target.value)}>
            {resumes.map((r) => (
              <option key={r.id} value={r.id}>
                {r.version_name}
                {r.is_default ? " (default)" : ""}
              </option>
            ))}
          </select>
        )}

        <h4 className="sheet-title">Cover letter for this job</h4>
        <textarea
          rows="6"
          value={coverLetter}
          onChange={(e) => setCoverLetter(e.target.value)}
          maxLength={3000}
          placeholder="Optional. Leave empty to skip it."
        />

        <label className="row" style={{ margin: "1rem 0 0" }}>
          <input
            type="checkbox"
            style={{ width: 20, height: 20, accentColor: "var(--orange)" }}
            checked={useAi}
            onChange={(e) => setUseAi(e.target.checked)}
          />
          <span>Let AI answer the extra questions I have not saved answers for</span>
        </label>
        <p className="never">
          Optional. Only the question and a few non-personal facts (skills, degree, years of
          experience) go to the AI. It never answers legal, salary, ID or diversity questions, and it
          leaves a field empty when it is not sure. Always check AI answers (purple outline).
        </p>

        {extension === null && <div className="ext-status checking">Checking for the SwipeX Autofill extension...</div>}
        {extension === true && <div className="ext-status on">SwipeX Autofill extension detected.</div>}
        {extension === false && (
          <div className="ext-status off">
            SwipeX Autofill extension not detected. Install it to fill forms automatically, or open
            the company page and fill it yourself.
          </div>
        )}

        {stage === "review" && (
          <>
            <button
              className="btn primary"
              onClick={startAutofill}
              disabled={busy || !payload.ready || !resumeId}
            >
              Fill the form and open the company page
            </button>
            <button
              className="btn"
              style={{ width: "100%", marginTop: "0.8rem" }}
              onClick={openWithoutAutofill}
              disabled={busy}
            >
              Open the company page without autofill
            </button>
          </>
        )}

        {stage === "waiting" && (
          <div className="apply-panel">
            <p className="muted small">
              Check every field on the company page, then submit it yourself. Come back and confirm
              when you are done.
            </p>
            <div className="actions">
              <button className="btn small primary-inline" onClick={markApplied} disabled={busy}>
                Yes, I applied
              </button>
              <button className="btn small" onClick={() => setStage("review")}>
                Not yet
              </button>
            </div>
          </div>
        )}

        {stage === "done" && (
          <Link className="btn small" to="/applications">
            Open applications
          </Link>
        )}
      </section>
    </div>
  );
}