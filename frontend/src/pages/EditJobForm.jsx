import { useState } from "react";
import api, { errorMessage } from "../api";

export default function EditJobForm({ job, onSaved, onCancel }) {
  const [form, setForm] = useState({
    title: job.title ?? "",
    description: job.description ?? "",
    location: job.is_remote ? "" : job.location ?? "",
    is_remote: !!job.is_remote,
    job_type: job.job_type === "internship" ? "internship" : "full_time",
    experience_level: job.experience_level ?? "fresher",
    salary_min_lpa: job.salary_min_lpa ?? "",
    salary_max_lpa: job.salary_max_lpa ?? "",
    skills: (job.skills ?? []).join(", "),
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function save(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { data } = await api.patch(`/recruiter/jobs/${job.id}`, {
        title: form.title.trim(),
        description: form.description.trim(),
        location: form.location.trim() || null,
        is_remote: form.is_remote,
        job_type: form.job_type,
        experience_level: form.experience_level,
        salary_min_lpa: form.salary_min_lpa === "" ? null : Number(form.salary_min_lpa),
        salary_max_lpa: form.salary_max_lpa === "" ? null : Number(form.salary_max_lpa),
        skills: form.skills.split(",").map((s) => s.trim()).filter(Boolean),
      });
      onSaved(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="applicants" onSubmit={save}>
      <h4 className="sheet-title" style={{ marginTop: 0 }}>
        Edit this job
      </h4>
      <label className="field">
        <span>Job title</span>
        <input value={form.title} onChange={set("title")} maxLength={200} required />
      </label>
      <label className="field">
        <span>Description</span>
        <textarea rows={6} value={form.description} onChange={set("description")} maxLength={5000} required />
      </label>
      <div className="grid2">
        <label className="field">
          <span>Location</span>
          <input value={form.location} onChange={set("location")} maxLength={120} disabled={form.is_remote} />
        </label>
        <label className="field">
          <span>Remote</span>
          <select
            value={form.is_remote ? "yes" : "no"}
            onChange={(e) => setForm({ ...form, is_remote: e.target.value === "yes" })}
          >
            <option value="no">No</option>
            <option value="yes">Yes, remote</option>
          </select>
        </label>
      </div>
      <div className="grid2">
        <label className="field">
          <span>Job type</span>
          <select value={form.job_type} onChange={set("job_type")}>
            <option value="full_time">Full-time</option>
            <option value="internship">Internship</option>
          </select>
        </label>
        <label className="field">
          <span>Experience level</span>
          <select value={form.experience_level} onChange={set("experience_level")}>
            <option value="fresher">Fresher</option>
            <option value="junior">Junior</option>
            <option value="mid">Mid-level</option>
            <option value="senior">Senior</option>
          </select>
        </label>
      </div>
      <div className="grid2">
        <label className="field">
          <span>Minimum salary (LPA)</span>
          <input type="number" min="0" max="500" step="0.1" value={form.salary_min_lpa} onChange={set("salary_min_lpa")} />
        </label>
        <label className="field">
          <span>Maximum salary (LPA)</span>
          <input type="number" min="0" max="500" step="0.1" value={form.salary_max_lpa} onChange={set("salary_max_lpa")} />
        </label>
      </div>
      <label className="field">
        <span>Skills (separate with commas)</span>
        <input value={form.skills} onChange={set("skills")} placeholder="Python, SQL, React" />
      </label>
      {error && <div className="msg error">{error}</div>}
      <div className="actions">
        <button className="btn small primary-inline" disabled={busy}>
          {busy ? "Saving..." : "Save changes"}
        </button>
        <button type="button" className="btn small" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}