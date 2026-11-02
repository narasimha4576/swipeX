import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const thisYear = new Date().getFullYear();
const blank = { school: "", degree: "", field_of_study: "", start_year: thisYear - 4, end_year: "", grade: "" };

export default function EducationSection() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(blank);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      const { data } = await api.get("/profile/educations");
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
      await api.post("/profile/educations", {
        school: form.school.trim(),
        degree: form.degree.trim(),
        field_of_study: form.field_of_study.trim() || null,
        start_year: Number(form.start_year),
        end_year: form.end_year === "" ? null : Number(form.end_year),
        grade: form.grade.trim() || null,
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
      await api.delete(`/profile/educations/${id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="glass card">
      <div className="section-head">
        <div>
          <h2>Education</h2>
          <p className="muted">Schools, colleges and courses.</p>
        </div>
        <button className="btn small" onClick={() => setOpen(!open)}>
          {open ? "Cancel" : "Add education"}
        </button>
      </div>

      {error && <div className="msg error">{error}</div>}

      {open && (
        <form onSubmit={add}>
          <label className="field">
            <span>School or college</span>
            <input value={form.school} onChange={set("school")} maxLength={200} required />
          </label>
          <div className="grid2">
            <label className="field">
              <span>Degree</span>
              <input value={form.degree} onChange={set("degree")} placeholder="e.g. B.Tech" maxLength={120} required />
            </label>
            <label className="field">
              <span>Field of study</span>
              <input value={form.field_of_study} onChange={set("field_of_study")} maxLength={120} />
            </label>
          </div>
          <div className="grid2">
            <label className="field">
              <span>Start year</span>
              <input type="number" min="1950" max="2100" value={form.start_year} onChange={set("start_year")} required />
            </label>
            <label className="field">
              <span>End year (empty = still studying)</span>
              <input type="number" min="1950" max="2100" value={form.end_year} onChange={set("end_year")} />
            </label>
          </div>
          <label className="field">
            <span>Grade (optional)</span>
            <input value={form.grade} onChange={set("grade")} placeholder="e.g. CGPA 8.2" maxLength={40} />
          </label>
          <button className="btn small primary-inline">Save</button>
        </form>
      )}

      {items.length === 0 && !open && <p className="muted">Nothing added yet.</p>}
      {items.map((x) => (
        <div className="item" key={x.id}>
          <div>
            <h3>
              {x.degree}
              {x.field_of_study ? `, ${x.field_of_study}` : ""}
            </h3>
            <div className="muted small">
              {x.school} | {x.start_year} - {x.end_year ?? "Present"}
              {x.grade ? ` | ${x.grade}` : ""}
            </div>
          </div>
          <div className="actions">
            <button className="btn small" onClick={() => remove(x.id)}>
              Delete
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}