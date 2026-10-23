import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const thisYear = new Date().getFullYear();
const blank = {
  company: "",
  title: "",
  start_year: thisYear,
  end_year: "",
  description: "",
};

export default function ExperienceSection() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(blank);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      const { data } = await api.get("/profile/experiences");
      setItems(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function add(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/profile/experiences", {
        company: form.company.trim(),
        title: form.title.trim(),
        start_year: Number(form.start_year),
        end_year: form.end_year === "" ? null : Number(form.end_year),
        description: form.description.trim() || null,
      });
      setForm(blank);
      setOpen(false);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(id) {
    setError("");
    try {
      await api.delete(`/profile/experiences/${id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="glass card">
      <div className="section-head">
        <div>
          <h2>Experience</h2>
          <p className="muted">Jobs, internships and projects all count.</p>
        </div>
        <button className="btn small" onClick={() => setOpen(!open)}>
          {open ? "Cancel" : "+ Add"}
        </button>
      </div>

      {error && <div className="msg error">{error}</div>}

      {open && (
        <form className="form-box" onSubmit={add}>
          <div className="grid2">
            <label className="field">
              <span>Company or organisation</span>
              <input value={form.company} onChange={set("company")} maxLength={200} required />
            </label>
            <label className="field">
              <span>Role or title</span>
              <input value={form.title} onChange={set("title")} maxLength={200} required />
            </label>
          </div>
          <div className="grid2">
            <label className="field">
              <span>Start year</span>
              <input type="number" min="1980" max="2100" value={form.start_year} onChange={set("start_year")} required />
            </label>
            <label className="field">
              <span>End year (leave empty if current)</span>
              <input type="number" min="1980" max="2100" value={form.end_year} onChange={set("end_year")} />
            </label>
          </div>
          <label className="field">
            <span>What did you do?</span>
            <textarea rows="3" value={form.description} onChange={set("description")} maxLength={1000} />
          </label>
          <button className="btn primary">Save experience</button>
        </form>
      )}

      {items.length === 0 && !open && <p className="muted">Nothing added yet.</p>}

      {items.map((x) => (
        <div className="item" key={x.id}>
          <div>
            <h3>
              {x.title} at {x.company}
            </h3>
            <div className="muted small">
              {x.start_year} - {x.end_year ?? "Present"}
            </div>
            {x.description && <p>{x.description}</p>}
          </div>
          <button className="btn small danger" onClick={() => remove(x.id)}>
            Remove
          </button>
        </div>
      ))}
    </section>
  );
}