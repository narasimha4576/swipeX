import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api";

export default function RecoverySection() {
  const [status, setStatus] = useState(null);
  const [codes, setCodes] = useState(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/recovery");
      setStatus(data);
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function create(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { data } = await api.post("/auth/recovery", { password: status?.created ? password : null });
      setCodes(data.codes);
      setPassword("");
      await load();
      window.dispatchEvent(new Event("swipex-recovery"));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  function download() {
    const text = [
      "SwipeX recovery codes",
      "Each code works once. Keep this file somewhere safe and private.",
      "",
      ...codes,
      "",
    ].join("\n");
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "swipex-recovery-codes.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  if (!status) return null;

  return (
    <section className="glass card">
      <h3>Recovery codes</h3>
      <p className="muted">
        If you forget your password, one of these codes lets you set a new one from the sign-in page. SwipeX does not
        send emails, so this is the only way back in. Each code works once.
      </p>

      {codes && (
        <>
          <div className="msg ok">
            Save these now. For your safety they are shown only this one time. Anyone with your email and one of these
            codes can reset your password.
          </div>
          <div className="codes-grid">
            {codes.map((code) => (
              <code key={code}>{code}</code>
            ))}
          </div>
          <div className="actions">
            <button className="btn small" onClick={copy}>
              {copied ? "Copied" : "Copy all"}
            </button>
            <button className="btn small" onClick={download}>
              Download as a file
            </button>
            <button className="btn small primary-inline" onClick={() => setCodes(null)}>
              I saved them
            </button>
          </div>
        </>
      )}

      {!codes && (
        <form onSubmit={create}>
          <p>
            {status.created
              ? `You have ${status.remaining} unused code${status.remaining === 1 ? "" : "s"}.`
              : "You have not made your recovery codes yet."}
          </p>
          {status.created && (
            <label className="field">
              <span>Your password (to make a new set, which replaces the old codes)</span>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
            </label>
          )}
          {error && <div className="msg error">{error}</div>}
          <button className="btn small primary-inline" disabled={busy}>
            {status.created ? "Make a new set of codes" : "Make my recovery codes"}
          </button>
        </form>
      )}
    </section>
  );
}