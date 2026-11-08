import { useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";

export default function ForgotPassword() {
  const [form, setForm] = useState({ email: "", code: "", password: "", again: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (form.password !== form.again) {
      setError("The two passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/forgot", {
        email: form.email.trim(),
        recovery_code: form.code.trim(),
        new_password: form.password,
      });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="public-wrap">
      <div className="brand" style={{ marginBottom: "1rem" }}>
        Swipe<span className="accent">X</span>
      </div>
      <section className="glass card">
        <h2>Forgot your password?</h2>
        {done ? (
          <>
            <p>Your password was changed. You can sign in with the new one now.</p>
            <Link className="btn primary" to="/login">
              Go to sign in
            </Link>
          </>
        ) : (
          <>
            <p className="muted">
              SwipeX does not send emails. Use one of the 8 recovery codes you saved in your Account page. Each code
              works once.
            </p>
            <form onSubmit={submit}>
              <label className="field">
                <span>Your email</span>
                <input type="email" value={form.email} onChange={set("email")} autoComplete="email" required />
              </label>
              <label className="field">
                <span>One recovery code (like K7QF-3M9X-R2DA)</span>
                <input value={form.code} onChange={set("code")} autoComplete="off" required />
              </label>
              <label className="field">
                <span>New password (at least 8 characters)</span>
                <input type="password" value={form.password} onChange={set("password")} autoComplete="new-password" required />
              </label>
              <label className="field">
                <span>New password again</span>
                <input type="password" value={form.again} onChange={set("again")} autoComplete="new-password" required />
              </label>
              {error && <div className="msg error">{error}</div>}
              <button className="btn primary" disabled={busy}>
                {busy ? "Saving..." : "Set new password"}
              </button>
            </form>
            <p className="muted small" style={{ marginTop: "1rem" }}>
              No codes saved? Then this account cannot be recovered from here. Passwords cannot be reset by anyone else,
              to keep your account private.
            </p>
            <p className="muted small">
              <Link className="link" to="/login">
                Back to sign in
              </Link>
            </p>
          </>
        )}
      </section>
    </div>
  );
}