import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const SECTION_LABEL = {
  summary: "Summary",
  education: "Education",
  experience: "Experience",
  projects: "Projects",
  skills: "Skills section",
  certifications: "Certifications",
};
const CONTACT_LABEL = { email: "Email", phone: "Phone", linkedin: "LinkedIn link", github: "GitHub link" };

function Check({ ok, label }) {
  return (
    <div className="signal">
      <span className={`signal-icon ${ok ? "ok" : "unknown"}`} style={{ fontSize: "0.8rem", fontWeight: 700 }}>
        {ok ? "+" : "-"}
      </span>
      <div>{label}</div>
    </div>
  );
}

export default function ResumeAnalysisPanel({ resumeId, onClose }) {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get(`/resumes/${resumeId}/analysis`)
      .then(({ data }) => {
        if (!cancelled) setInfo(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [resumeId]);

  async function addSkills() {
    setError("");
    setOk("");
    try {
      const { data: profile } = await api.get("/profile/me");
      const have = new Set(profile.skills.map((s) => s.toLowerCase()));
      const merged = [...profile.skills, ...info.skills.filter((s) => !have.has(s.toLowerCase()))].slice(0, 30);
      await api.put("/profile/me", {
        headline: profile.headline,
        location: profile.location,
        experience_years: profile.experience_years,
        skills: merged,
        bio: profile.bio,
      });
      setOk(`Your profile now lists ${merged.length} skills. Refresh the page to see them.`);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="match-card">
      <div className="row between">
        <h4 className="sheet-title" style={{ margin: 0 }}>
          Resume check{info ? `: ${info.name}` : ""}
        </h4>
        <button className="btn small" onClick={onClose}>
          Close
        </button>
      </div>

      {!info && !error && <p className="muted small">Reading your resume...</p>}
      {error && <div className="msg error">{error}</div>}
      {ok && <div className="msg ok">{ok}</div>}

      {info && (
        <>
          <div className="score-row">
            <div className="score-big">{info.score}</div>
            <div style={{ flex: 1 }}>
              <div className="muted small">Resume health out of 100</div>
              <div className="meter">
                <div style={{ width: info.score + "%" }} />
              </div>
              <div className="muted small">
                {info.pages} page{info.pages === 1 ? "" : "s"} | {info.words} words
              </div>
            </div>
          </div>

          <h4 className="sheet-title">Checks</h4>
          {Object.entries(CONTACT_LABEL).map(([key, label]) => (
            <Check key={key} ok={info.contact[key]} label={label} />
          ))}
          {Object.entries(SECTION_LABEL).map(([key, label]) => (
            <Check key={key} ok={info.sections[key]} label={label} />
          ))}

          <h4 className="sheet-title">Skills found ({info.skills.length})</h4>
          {info.skills.length === 0 && <p className="muted small">No known skills were found.</p>}
          <div className="chips">
            {info.skills.map((s) => (
              <span className="chip good" key={s}>
                {s}
              </span>
            ))}
          </div>
          {info.skills.length > 0 && (
            <button className="btn small" style={{ marginTop: "0.8rem" }} onClick={addSkills}>
              Add these skills to my profile
            </button>
          )}

          <h4 className="sheet-title">Tips</h4>
          <ul className="tips-list">
            {info.tips.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}