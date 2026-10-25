import { useEffect, useRef, useState } from "react";
import api, { errorMessage } from "../api";

export default function ResumeSection() {
  const [resumes, setResumes] = useState([]);
  const [name, setName] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);

  async function load() {
    try {
      const { data } = await api.get("/resumes");
      setResumes(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function upload(e) {
    e.preventDefault();
    setError("");
    setOk("");
    if (!file) {
      setError("Choose a PDF file first");
      return;
    }
    const form = new FormData();
    form.append("version_name", name.trim());
    form.append("file", file);
    setBusy(true);
    try {
      await api.post("/resumes", form);
      setName("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      setOk("Resume uploaded");
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function view(id) {
    setError("");
    const win = window.open("", "_blank");
    if (!win) {
      setError("Please allow pop-ups to view the file");
      return;
    }
    try {
      const { data } = await api.get(`/resumes/${id}/file`, { responseType: "blob" });
      win.location.href = URL.createObjectURL(data);
    } catch (err) {
      win.close();
      setError(errorMessage(err));
    }
  }

  async function makeDefault(id) {
    setError("");
    try {
      await api.patch(`/resumes/${id}/default`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(id) {
    setError("");
    setOk("");
    try {
      await api.delete(`/resumes/${id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="glass card">
      <h2>Resumes</h2>
      <p className="muted">Upload up to 5 PDF versions and pick one when you apply.</p>

      {error && <div className="msg error">{error}</div>}
      {ok && <div className="msg ok">{ok}</div>}

      <form className="form-box" onSubmit={upload}>
        <label className="field">
          <span>Resume name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
            placeholder="e.g. AI/ML resume"
            required
          />
        </label>
        <label className="field">
          <span>PDF file (up to 5 MB)</span>
          <input
            ref={fileInput}
            type="file"
            accept="application/pdf,.pdf"
            onChange={(e) => setFile(e.target.files[0] ?? null)}
          />
        </label>
        <button className="btn primary" disabled={busy}>
          {busy ? "Uploading..." : "Upload resume"}
        </button>
      </form>

      {resumes.length === 0 && <p className="muted">No resumes yet.</p>}

      {resumes.map((r) => (
        <div className="item" key={r.id}>
          <div>
            <h3>{r.version_name}</h3>
            <div className="row" style={{ flexWrap: "wrap" }}>
              {r.is_default && <span className="badge job_seeker">Default</span>}
              <span className="muted small">Uploaded {r.created_at.slice(0, 10)}</span>
            </div>
          </div>
          <div className="actions">
            <button className="btn small" onClick={() => view(r.id)}>
              View
            </button>
            {!r.is_default && (
              <button className="btn small" onClick={() => makeDefault(r.id)}>
                Make default
              </button>
            )}
            <button className="btn small danger" onClick={() => remove(r.id)}>
              Delete
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}