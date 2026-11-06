import { useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import { useAuth } from "../authContext";

export default function AccountPage() {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");

  async function download() {
    setNote("");
    setBusy(true);
    try {
      const { data } = await api.get("/account/export", { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "swipex-my-data.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setNote("Your download has started.");
    } catch (err) {
      setNote(
        err?.response?.status === 429
          ? "You can download your data up to 5 times an hour. Please try again later."
          : "Could not prepare your download. Please try again in a moment."
      );
    } finally {
      setBusy(false);
    }
  }

  async function remove(event) {
    event.preventDefault();
    setError("");
    if (!window.confirm("This cannot be undone. Delete your account and your data?")) return;
    setBusy(true);
    try {
      await api.post("/account/delete", { password, confirm });
      localStorage.removeItem("swipex_token");
      window.location.assign("/login");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <>
      <section className="glass card">
        <h2>Your account</h2>
        <p>
          {user.full_name} <span className="muted">({user.email})</span>
        </p>
        <p className="muted small">
          <Link className="link" to="/privacy">
            Privacy Policy
          </Link>{" "}
          |{" "}
          <Link className="link" to="/terms">
            Terms of Use
          </Link>
        </p>
      </section>

      <section className="glass card">
        <h3>Download your data</h3>
        <p className="muted">
          Get a ZIP file with everything SwipeX holds about you: your details, resumes, photo and activity. It never
          includes your password or other people's data.
        </p>
        <button className="btn small primary-inline" onClick={download} disabled={busy}>
          Download my data
        </button>
        {note && <p className="muted small">{note}</p>}
      </section>

      <section className="glass card">
        <h3>Delete your account</h3>
        {user.role === "admin" ? (
          <p className="muted">Admin accounts cannot be deleted from the website.</p>
        ) : (
          <>
            <p className="muted">
              This permanently erases your profile, resumes, photo, applications, liked and skipped jobs, saved searches
              and notifications.
              {user.role === "recruiter" &&
                " Job postings and your company record stay, closed, so applicants keep their history. If you started a team, remove its other members first."}{" "}
              You can sign up again later with the same email.
            </p>
            <form onSubmit={remove}>
              <label className="field">
                <span>Your password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </label>
              <label className="field">
                <span>Type DELETE to confirm</span>
                <input value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
              </label>
              {error && <div className="msg error">{error}</div>}
              <button className="btn small" disabled={busy || confirm.trim().toUpperCase() !== "DELETE" || !password}>
                Delete my account
              </button>
            </form>
          </>
        )}
      </section>
    </>
  );
}