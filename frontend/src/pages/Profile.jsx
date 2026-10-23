import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const empty = {
  headline: "",
  location: "",
  experience_years: 0,
  skills: [],
  bio: "",
};

function normalize(data) {
  return {
    headline: data.headline ?? "",
    location: data.location ?? "",
    experience_years: data.experience_years ?? 0,
    skills: data.skills ?? [],
    bio: data.bio ?? "",
  };
}

export default function Profile() {
  const [form, setForm] = useState(empty);
  const [skillInput, setSkillInput] = useState("");
  const [status, setStatus] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/profile/me")
      .then(({ data }) => setForm(normalize(data)))
      .catch((err) => setStatus({ type: "error", text: errorMessage(err) }))
      .finally(() => setLoading(false));
  }, []);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  function addSkills() {
    const parts = skillInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!parts.length) return;
    setForm((f) => {
      const have = new Set(f.skills.map((s) => s.toLowerCase()));
      const next = [...f.skills];
      parts.forEach((p) => {
        if (!have.has(p.toLowerCase())) {
          have.add(p.toLowerCase());
          next.push(p);
        }
      });
      return { ...f, skills: next };
    });
    setSkillInput("");
  }

  function removeSkill(skill) {
    setForm((f) => ({ ...f, skills: f.skills.filter((s) => s !== skill) }));
  }

  async function save(e) {
    e.preventDefault();
    setStatus({ type: "", text: "" });
    try {
      const payload = {
        headline: form.headline.trim() || null,
        location: form.location.trim() || null,
        experience_years: Number(form.experience_years) || 0,
        skills: form.skills,
        bio: form.bio.trim() || null,
      };
      const { data } = await api.put("/profile/me", payload);
      setForm(normalize(data));
      setStatus({ type: "ok", text: "Profile saved" });
    } catch (err) {
      setStatus({ type: "error", text: errorMessage(err) });
    }
  }

  const strength =
    (form.headline.trim() ? 25 : 0) +
    (form.location.trim() ? 25 : 0) +
    (form.bio.trim() ? 25 : 0) +
    (form.skills.length >= 3 ? 25 : 0);

  if (loading) return <div className="muted">Loading profile...</div>;

  return (
    <section className="glass card">
      <div className="row between">
        <div>
          <h2>My profile</h2>
          <p className="muted">Your skills and experience power your job matches.</p>
        </div>
        <div className="meter-wrap">
          <div className="muted small">Profile strength {strength}%</div>
          <div className="meter">
            <div style={{ width: `${strength}%` }} />
          </div>
        </div>
      </div>

      <form onSubmit={save}>
        <label className="field">
          <span>Headline</span>
          <input
            value={form.headline}
            onChange={set("headline")}
            maxLength={200}
            placeholder="e.g. AI/ML fresher interested in backend and GenAI"
          />
        </label>

        <div className="grid2">
          <label className="field">
            <span>Location</span>
            <input
              value={form.location}
              onChange={set("location")}
              maxLength={120}
              placeholder="City, Country"
            />
          </label>
          <label className="field">
            <span>Years of experience</span>
            <input
              type="number"
              min="0"
              max="60"
              step="0.5"
              value={form.experience_years}
              onChange={set("experience_years")}
            />
          </label>
        </div>

        <div className="field">
          <span>Skills</span>
          <div className="row">
            <input
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === ",") {
                  e.preventDefault();
                  addSkills();
                }
              }}
              placeholder="Type a skill and press Enter (or paste: Python, SQL, FastAPI)"
            />
            <button type="button" className="btn" onClick={addSkills}>
              Add
            </button>
          </div>
          <div className="chips">
            {form.skills.map((s) => (
              <span className="chip" key={s}>
                {s}
                <button type="button" onClick={() => removeSkill(s)} aria-label={`Remove ${s}`}>
                  x
                </button>
              </span>
            ))}
          </div>
        </div>

        <label className="field">
          <span>About you</span>
          <textarea
            rows="4"
            value={form.bio}
            onChange={set("bio")}
            maxLength={2000}
            placeholder="A few lines about what you are learning and building"
          />
        </label>

        {status.text && <div className={`msg ${status.type}`}>{status.text}</div>}

        <button className="btn primary">Save profile</button>
      </form>
    </section>
  );
}