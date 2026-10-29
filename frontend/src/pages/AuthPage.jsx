import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { errorMessage } from "../api";
import ThemeToggle from "./ThemeToggle";

export default function AuthPage() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: "job_seeker",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <ThemeToggle floating />
      <div className="auth-wrap">
        <div className="hero">
          <div className="cube-scene" aria-hidden="true">
            <div className="cube">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
          <h1>
            Swipe<span className="accent">X</span>
          </h1>
          <p className="muted">
            Swipe right on your next role. AI-powered job discovery for freshers
            and professionals.
          </p>
        </div>

        <form className="glass card auth-card" onSubmit={submit}>
          <div className="tabs">
            <button
              type="button"
              className={mode === "login" ? "tab active" : "tab"}
              onClick={() => setMode("login")}
            >
              Log in
            </button>
            <button
              type="button"
              className={mode === "register" ? "tab active" : "tab"}
              onClick={() => setMode("register")}
            >
              Sign up
            </button>
          </div>

          {mode === "register" && (
            <label className="field">
              <span>Full name</span>
              <input value={form.full_name} onChange={set("full_name")} required />
            </label>
          )}

          <label className="field">
            <span>Email</span>
            <input type="email" value={form.email} onChange={set("email")} required />
          </label>

          <label className="field">
            <span>Password</span>
            <div className="password-wrap">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={set("password")}
                minLength={mode === "register" ? 8 : undefined}
                required
              />
              <button
                type="button"
                className="eye"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.9 17.9A10.1 10.1 0 0 1 12 20c-6.5 0-10-8-10-8a18 18 0 0 1 4.1-5.2M9.9 4.2A9.7 9.7 0 0 1 12 4c6.5 0 10 8 10 8a18 18 0 0 1-2.2 3.3" />
                    <path d="M14.1 14.1a3 3 0 1 1-4.2-4.2" />
                    <path d="M2 2l20 20" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 12s3.5-8 10-8 10 8 10 8-3.5 8-10 8-10-8-10-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </label>

          {mode === "register" && (
            <label className="field">
              <span>I am a</span>
              <select value={form.role} onChange={set("role")}>
                <option value="job_seeker">Job seeker</option>
                <option value="recruiter">Recruiter</option>
              </select>
            </label>
          )}

          {error && <div className="msg error">{error}</div>}

          <button className="btn primary" disabled={busy}>
            {busy
              ? "Please wait..."
              : mode === "login"
              ? "Log in"
              : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}