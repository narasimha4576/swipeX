import { useState } from "react";
import api, { errorMessage } from "../api";

export default function PasswordSection() {
  const [form, setForm] = useState({ current: "", next: "", again: "" });
  const [note, setNote] = useState({ type: "", text: "" });
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setNote({ type: "", text: "" });
    if (form.next !== form.again) {
      setNote({ type: "error", text: "The two new passwords do not match" });
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/change-password", { current_password: form.current, new_password: form.next });
      setForm({ current: "", next: "", again: "" });
      setNote({ type: "ok", text: "Your password was changed." });
    } catch (err) {
      setNote({ type: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="glass card">
      <h3>Change your password</h3>
      <form onSubmit={submit}>
        <label className="field">
          <span>Current password</span>
          <input type="password" value={form.current} onChange={set("current")} autoComplete="current-password" required />
        </label>
        <div className="grid2">
          <label className="field">
            <span>New password (at least 8 characters)</span>
            <input type="password" value={form.next} onChange={set("next")} autoComplete="new-password" required />
          </label>
          <label className="field">
            <span>New password again</span>
            <input type="password" value={form.again} onChange={set("again")} autoComplete="new-password" required />
          </label>
        </div>
        {note.text && <div className={note.type === "error" ? "msg error" : "msg ok"}>{note.text}</div>}
        <button className="btn small primary-inline" disabled={busy}>
          Change password
        </button>
      </form>
    </section>
  );
}