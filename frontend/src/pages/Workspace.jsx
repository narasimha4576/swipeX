import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import MyPostingsList from "./MyPostings";
import VerificationCard from "./VerificationCard";
import {
  COMP_LABEL,
  JOB_TYPE_LABEL,
  LEVEL_LABEL,
  TYPE_LABEL,
  logoColor,
  salary,
  timeAgo,
} from "../jobUtils";

const emptyCompany = {
  name: "",
  company_type: "startup",
  location: "",
  website: "",
  founded_year: "",
};

const emptyJob = {
  title: "",
  description: "",
  location: "",
  is_remote: false,
  job_type: "full_time",
  experience_level: "fresher",
  salary_min_lpa: "",
  salary_max_lpa: "",
  skills: [],
};

function fromCompany(c) {
  return {
    name: c.name,
    company_type: c.company_type,
    location: c.location ?? "",
    website: c.website ?? "",
    founded_year: c.founded_year ?? "",
  };
}

function CompanySection({ company, onSaved }) {
  const [editing, setEditing] = useState(!company);
  const [form, setForm] = useState(company ? fromCompany(company) : emptyCompany);
  const [error, setError] = useState("");

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function save(e) {
    e.preventDefault();
    setError("");
    try {
      const { data } = await api.put("/recruiter/company", {
        name: form.name.trim(),
        company_type: form.company_type,
        location: form.location.trim() || null,
        website: form.website.trim() || null,
        founded_year: form.founded_year === "" ? null : Number(form.founded_year),
      });
      onSaved(data);
      setForm(fromCompany(data));
      setEditing(false);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (!editing && company) {
    const details = [company.location, company.founded_year ? `Founded ${company.founded_year}` : null]
      .filter(Boolean)
      .join("  |  ");
    return (
      <section className="glass card">
        <div className="job-top">
          <div className="logo" style={{ background: logoColor(company.name) }}>
            {company.name.charAt(0)}
          </div>
          <div className="job-title">
            <h2>{company.name}</h2>
            <div className="muted small">{details}</div>
          </div>
          <span className={`badge ${company.company_type}`}>
            {TYPE_LABEL[company.company_type] ?? company.company_type}
          </span>
        </div>
        {company.website && (
          <p>
            <a className="link" href={company.website} target="_blank" rel="noreferrer">
              {company.website}
            </a>
          </p>
        )}
        <button className="btn small" onClick={() => setEditing(true)}>
          Edit company
        </button>
      </section>
    );
  }

  return (
    <section className="glass card">
      <h2>{company ? "Edit company" : "Set up your company"}</h2>
      <p className="muted">Job seekers see this on every job you post.</p>
      <form onSubmit={save}>
        <label className="field">
          <span>Company name</span>
          <input value={form.name} onChange={set("name")} maxLength={200} required />
        </label>
        <div className="grid2">
          <label className="field">
            <span>Company type</span>
            <select value={form.company_type} onChange={set("company_type")}>
              <option value="mnc">MNC</option>
              <option value="startup">Startup</option>
              <option value="new_startup">Newly founded startup</option>
            </select>
          </label>
          <label className="field">
            <span>Founded year</span>
            <input
              type="number"
              min="1800"
              max="2100"
              value={form.founded_year}
              onChange={set("founded_year")}
            />
          </label>
        </div>
        <div className="grid2">
          <label className="field">
            <span>City</span>
            <input value={form.location} onChange={set("location")} maxLength={120} />
          </label>
          <label className="field">
            <span>Website</span>
            <input
              value={form.website}
              onChange={set("website")}
              maxLength={255}
              placeholder="https://"
            />
          </label>
        </div>
        {error && <div className="msg error">{error}</div>}
        <div className="row">
          <button className="btn primary">Save company</button>
          {company && (
            <button type="button" className="btn" onClick={() => setEditing(false)}>
              Cancel
            </button>
          )}
        </div>
      </form>
    </section>
  );
}

function PostJobSection({ company, onPosted }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyJob);
  const [skillInput, setSkillInput] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");

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

  async function submit(e) {
    e.preventDefault();
    setError("");
    setOk("");
    const min = form.salary_min_lpa === "" ? null : Number(form.salary_min_lpa);
    const max = form.salary_max_lpa === "" ? null : Number(form.salary_max_lpa);
    try {
      await api.post("/recruiter/jobs", {
        title: form.title.trim(),
        description: form.description.trim(),
        location: form.location.trim() || null,
        is_remote: form.is_remote,
        job_type: form.job_type,
        experience_level: form.experience_level,
        salary_min_lpa: min,
        salary_max_lpa: max,
        skills: form.skills,
      });
      setForm(emptyJob);
      setSkillInput("");
      setOpen(false);
      setOk("Job posted. It is now live for job seekers.");
      onPosted();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (!company) {
    return (
      <section className="glass card">
        <h2>Post a job</h2>
        <p className="muted">Set up your company first, then you can post jobs.</p>
      </section>
    );
  }

  return (
    <section className="glass card">
      <div className="section-head">
        <div>
          <h2>Post a job</h2>
          <p className="muted">New jobs appear instantly in Jobs and Discover.</p>
        </div>
        <button className="btn small" onClick={() => setOpen(!open)}>
          {open ? "Cancel" : "+ New job"}
        </button>
      </div>

      {ok && <div className="msg ok">{ok}</div>}

      {open && (
        <form onSubmit={submit}>
          <label className="field">
            <span>Job title</span>
            <input value={form.title} onChange={set("title")} maxLength={200} required />
          </label>
          <label className="field">
            <span>Description (at least 20 characters)</span>
            <textarea
              rows="5"
              value={form.description}
              onChange={set("description")}
              maxLength={5000}
              required
            />
          </label>
          <div className="grid2">
            <label className="field">
              <span>Location</span>
              <input
                value={form.location}
                onChange={set("location")}
                maxLength={120}
                placeholder="City"
              />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={form.is_remote}
                onChange={(e) => setForm({ ...form, is_remote: e.target.checked })}
              />
              <span>Remote job</span>
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
              <input
                type="number"
                min="0"
                step="0.5"
                value={form.salary_min_lpa}
                onChange={set("salary_min_lpa")}
              />
            </label>
            <label className="field">
              <span>Maximum salary (LPA)</span>
              <input
                type="number"
                min="0"
                step="0.5"
                value={form.salary_max_lpa}
                onChange={set("salary_max_lpa")}
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
                placeholder="Type a skill and press Enter"
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

          {error && <div className="msg error">{error}</div>}
          <button className="btn primary">Post job</button>
        </form>
      )}
    </section>
  );
}


export default function Workspace() {
  const [company, setCompany] = useState(undefined);
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState("");

  async function loadJobs() {
    try {
      const { data } = await api.get("/recruiter/jobs");
      setJobs(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    api
      .get("/recruiter/company")
      .then(({ data }) => setCompany(data))
      .catch((err) => {
        setError(errorMessage(err));
        setCompany(null);
      });
    loadJobs();
  }, []);

  async function toggle(job) {
    setError("");
    try {
      await api.patch(`/recruiter/jobs/${job.id}/active`, null, {
        params: { is_active: !job.is_active },
      });
      loadJobs();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (company === undefined) {
    return <p className="muted">Loading workspace...</p>;
  }

  return (
    <>
      <section>
        <div className="section-head">
          <div>
            <h2>Workspace</h2>
            <p className="muted">Manage your company and your job postings.</p>
          </div>
        </div>
        {error && <div className="msg error">{error}</div>}
      </section>
      <CompanySection company={company} onSaved={setCompany} />
      {company && <VerificationCard key={company.name + (company.website ?? "")} company={company} />}
      <PostJobSection company={company} onPosted={loadJobs} />
      <MyPostingsList jobs={jobs} onToggle={toggle} />
    </>
  );
}