import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const blank = { title: "", url: "", description: "" };

export default function PortfolioSection() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(blank);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    try {
      const { data } = await api.get("/profile/portfolio");
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
      await api.post("/profile/portfolio", {
        title: form.title.trim(),
        url: form.url.trim(),
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
      await api.delete(`/profile/portfolio/${id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="glass card">
      <div className="section-head">
        <div>
          <h2>Portfolio</h2>
          <p className="muted">Links to your GitHub, projects and demos.</p>
        </div>
        <button className="btn small" onClick={() => setOpen(!open)}>
          {open ? "Cancel" : "+ Add"}
        </button>
      </div>

      {error && <div className="msg error">{error}</div>}

      {open && (
        <form className="form-box" onSubmit={add}>
          <label className="field">
            <span>Title</span>
            <input value={form.title} onChange={set("title")} maxLength={200} required />
          </label>
          <label className="field">
            <span>Link</span>
            <input value={form.url} onChange={set("url")} maxLength={500} placeholder="https://" required />
          </label>
          <label className="field">
            <span>Short description</span>
            <input value={form.description} onChange={set("description")} maxLength={500} />
          </label>
          <button className="btn primary">Save link</button>
        </form>
      )}

      {items.length === 0 && !open && <p className="muted">Nothing added yet.</p>}

      {items.map((x) => (
        <div className="item" key={x.id}>
          <div>
            <h3>{x.title}</h3>
            <a href={x.url} target="_blank" rel="noreferrer">
              {x.url}
            </a>
            {x.description && <p className="muted">{x.description}</p>}
          </div>
          <button className="btn small danger" onClick={() => remove(x.id)}>
            Remove
          </button>
        </div>
      ))}
    </section>
  );
}