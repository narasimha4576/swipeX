import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import { useAuth } from "../authContext";

export default function FeedbackPage() {
  const auth = useAuth();
  const user = auth?.user ?? null;
  const [params] = useSearchParams();
  const from = params.get("from") || "";
  const [kind, setKind] = useState(params.get("type") === "problem" ? "problem" : "feedback");
  const [message, setMessage] = useState("");
  const [rating, setRating] = useState(null);
  const [errorRef, setErrorRef] = useState(params.get("ref") || "");
  const [contactOk, setContactOk] = useState(false);
  const [contactEmail, setContactEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/feedback", {
        kind,
        message,
        rating: kind === "feedback" ? rating : null,
        page: from || null,
        error_ref: kind === "problem" && errorRef.trim() ? errorRef.trim() : null,
        contact_ok: user ? contactOk : false,
        contact_email: !user && contactEmail.trim() ? contactEmail.trim() : null,
      });
      setSent(true);
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
        {sent ? (
          <>
            <h2>Thank you</h2>
            <p>
              {kind === "problem"
                ? "Your report was sent. It helps us fix things."
                : "Your feedback was sent. We read every message."}
            </p>
            <Link className="btn primary" to="/">
              Back to SwipeX
            </Link>
          </>
        ) : (
          <>
            <h2>Help us improve SwipeX</h2>
            <div className="tabs" style={{ marginBottom: "1rem" }}>
              <button type="button" className={"tab" + (kind === "feedback" ? " active" : "")} onClick={() => setKind("feedback")}>
                Feedback
              </button>
              <button type="button" className={"tab" + (kind === "problem" ? " active" : "")} onClick={() => setKind("problem")}>
                Report a problem
              </button>
            </div>
            <form onSubmit={submit}>
              <label className="field">
                <span>{kind === "problem" ? "What went wrong? What did you expect to happen?" : "What would you like us to know?"}</span>
                <textarea rows={6} value={message} onChange={(e) => setMessage(e.target.value)} maxLength={2000} required />
              </label>

              {kind === "feedback" && (
                <div className="field">
                  <span>How is SwipeX for you? (optional)</span>
                  <div className="chip-wrap">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button type="button" key={n} className={rating === n ? "fchip on" : "fchip"} onClick={() => setRating(rating === n ? null : n)}>
                        {n} {n === 1 ? "star" : "stars"}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {kind === "problem" && (
                <label className="field">
                  <span>Reference code, if the page showed one (optional)</span>
                  <input value={errorRef} onChange={(e) => setErrorRef(e.target.value)} maxLength={16} placeholder="for example 3F9A1C2B" />
                </label>
              )}

              {user ? (
                <label className="note-pref" style={{ borderTop: 0, padding: "0 0 0.8rem" }}>
                  <input type="checkbox" checked={contactOk} onChange={(e) => setContactOk(e.target.checked)} />
                  <span>You may contact me about this (your name and account email are shown to the SwipeX admin)</span>
                </label>
              ) : (
                <label className="field">
                  <span>Your email, if you want a reply (optional)</span>
                  <input type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} maxLength={200} />
                </label>
              )}

              <p className="muted small">
                {from ? `About the page: ${from}. ` : ""}A short description of your browser is attached to help us find
                bugs. {user ? "Without the tick box above, this stays anonymous." : "You are not signed in, so this is anonymous."}
              </p>
              {error && <div className="msg error">{error}</div>}
              <div className="actions">
                <button className="btn primary" disabled={busy}>
                  {busy ? "Sending..." : "Send"}
                </button>
                <Link className="btn" to={user ? "/" : "/login"}>
                  Cancel
                </Link>
              </div>
            </form>
          </>
        )}
      </section>
    </div>
  );
}