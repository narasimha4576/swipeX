import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const EMPTY = {
  phone: "",
  linkedin_url: "",
  github_url: "",
  portfolio_url: "",
  college: "",
  degree: "",
  discipline: "",
  graduation_year: "",
  authorized_countries: "",
  requires_sponsorship: false,
  willing_to_relocate: false,
  notice_period_days: "",
  current_ctc_lpa: "",
  expected_ctc_lpa: "",
  cover_letter: "",
};

const LETTER_HINT =
  "Optional. You can use {{name}}, {{company}} and {{job_title}}. They are replaced for each job.";

function fromServer(data) {
  return Object.fromEntries(Object.keys(EMPTY).map((key) => [key, data[key] ?? EMPTY[key]]));
}

function toServer(form) {
  const text = (value) => (String(value).trim() ? String(value).trim() : null);
  const number = (value) => (value === "" ? null : Number(value));
  return {
    phone: text(form.phone),
    linkedin_url: text(form.linkedin_url),
    github_url: text(form.github_url),
    portfolio_url: text(form.portfolio_url),
    college: text(form.college),
    degree: text(form.degree),
    discipline: text(form.discipline),
    graduation_year: number(form.graduation_year),
    authorized_countries: text(form.authorized_countries),
    requires_sponsorship: form.requires_sponsorship,
    willing_to_relocate: form.willing_to_relocate,
    notice_period_days: number(form.notice_period_days),
    current_ctc_lpa: number(form.current_ctc_lpa),
    expected_ctc_lpa: number(form.expected_ctc_lpa),
    cover_letter: text(form.cover_letter),
  };
}

export default function ApplicationDetailsSection() {
  const [form, setForm] = useState(EMPTY);
  const [missing, setMissing] = useState([]);
  const [status, setStatus] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/autofill/details")
      .then(({ data }) => {
        setForm(fromServer(data));
        setMissing(data.missing);
      })
      .catch((err) => setStatus({ type: "error", text: errorMessage(err) }))
      .finally(() => setLoading(false));
  }, []);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const toggle = (key) => (e) => setForm({ ...form, [key]: e.target.checked });

  async function save(e) {
    e.preventDefault();
    setStatus({ type: "", text: "" });
    try {
      for (const [key, label] of [
        ["current_ctc_lpa", "Current CTC"],
        ["expected_ctc_lpa", "Expected CTC"],
      ]) {
        if (form[key] !== "" && Number(form[key]) > 1000) {
          setStatus({
            type: "error",
            text: `${label} is in lakhs per year. Enter 6.5 for 6,50,000 rupees, not the full amount.`,
          });
          return;
        }
      }
      const { data } = await api.put("/autofill/details", toServer(form));
      setForm(fromServer(data));
      setMissing(data.missing);
      setStatus({ type: "ok", text: "Application details saved" });
    } catch (err) {
      setStatus({ type: "error", text: errorMessage(err) });
    }
  }

  if (loading) return <p className="muted">Loading application details...</p>;

  return (
    <section className="glass card wide">
      <div className="row between">
        <div>
          <h2>Application details</h2>
          <p className="muted">
            Companies ask for the same things again and again. Save them once and SwipeX fills them
            for you. You always check everything before you submit.
          </p>
        </div>
        {missing.length === 0 ? (
          <span className="badge verified">Ready for autofill</span>
        ) : (
          <span className="badge pending">Missing: {missing.join(", ")}</span>
        )}
      </div>

      <form onSubmit={save}>
        <div className="grid2">
          <label className="field">
            <span>Phone (with country code)</span>
            <input value={form.phone} onChange={set("phone")} placeholder="+91 98765 43210" />
          </label>
          <label className="field">
            <span>LinkedIn link</span>
            <input value={form.linkedin_url} onChange={set("linkedin_url")} placeholder="https://" />
          </label>
        </div>
        <div className="grid2">
          <label className="field">
            <span>GitHub link</span>
            <input value={form.github_url} onChange={set("github_url")} placeholder="https://" />
          </label>
          <label className="field">
            <span>Portfolio or website</span>
            <input value={form.portfolio_url} onChange={set("portfolio_url")} placeholder="https://" />
          </label>
        </div>

        <div className="grid2">
          <label className="field">
            <span>College or university</span>
            <input value={form.college} onChange={set("college")} maxLength={200} />
          </label>
          <label className="field">
            <span>Graduation year</span>
            <input
              type="number"
              min="1980"
              max="2100"
              value={form.graduation_year}
              onChange={set("graduation_year")}
            />
          </label>
        </div>
        <div className="grid2">
          <label className="field">
            <span>Degree</span>
            <input value={form.degree} onChange={set("degree")} placeholder="e.g. B.Tech" maxLength={100} />
          </label>
          <label className="field">
            <span>Discipline or major</span>
            <input value={form.discipline} onChange={set("discipline")} maxLength={100} />
          </label>
        </div>

        <div className="grid2">
          <label className="field">
            <span>Countries you can legally work in</span>
            <input
              value={form.authorized_countries}
              onChange={set("authorized_countries")}
              placeholder="e.g. India"
              maxLength={200}
            />
          </label>
          <label className="field">
            <span>Notice period (days)</span>
            <input
              type="number"
              min="0"
              max="365"
              value={form.notice_period_days}
              onChange={set("notice_period_days")}
            />
          </label>
        </div>
        <div className="grid2">
          <label className="field">
            <span>Current CTC (lakhs per year, e.g. 6.5)</span>
            <input
              type="number"
              min="0"
              step="0.1"
              max="1000"
              value={form.current_ctc_lpa}
              onChange={set("current_ctc_lpa")}
            />
          </label>
          <label className="field">
            <span>Expected CTC (lakhs per year, e.g. 8)</span>
            <input
              type="number"
              min="0"
              step="0.1"
              max="1000"
              value={form.expected_ctc_lpa}
              onChange={set("expected_ctc_lpa")}
            />
          </label>
        </div>

        <div className="row" style={{ flexWrap: "wrap", gap: "1.5rem", marginBottom: "1rem" }}>
          <label className="row">
            <input
              type="checkbox"
              style={{ width: 20, height: 20, accentColor: "var(--orange)" }}
              checked={form.requires_sponsorship}
              onChange={toggle("requires_sponsorship")}
            />
            <span>I need visa sponsorship</span>
          </label>
          <label className="row">
            <input
              type="checkbox"
              style={{ width: 20, height: 20, accentColor: "var(--orange)" }}
              checked={form.willing_to_relocate}
              onChange={toggle("willing_to_relocate")}
            />
            <span>I am willing to relocate</span>
          </label>
        </div>

        <label className="field">
          <span>Default cover letter</span>
          <textarea
            rows="5"
            value={form.cover_letter}
            onChange={set("cover_letter")}
            maxLength={3000}
            placeholder={"Hello {{company}} team, I am excited to apply for the {{job_title}} role..."}
          />
        </label>
        <p className="muted small">{LETTER_HINT}</p>

        {status.text && <div className={`msg ${status.type}`}>{status.text}</div>}
        <button className="btn primary">Save application details</button>
      </form>
    </section>
  );
}