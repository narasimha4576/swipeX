import { useEffect, useRef, useState } from "react";
import api, { errorMessage } from "../api";

export default function PhotoAndSharing() {
  const [extras, setExtras] = useState(null);
  const [msg, setMsg] = useState({ type: "", text: "" });
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);

  async function run(call, okText) {
    setMsg({ type: "", text: "" });
    setBusy(true);
    try {
      const { data } = await call();
      setExtras(data);
      if (okText) setMsg({ type: "ok", text: okText });
      window.dispatchEvent(new Event("swipex-photo"));
    } catch (err) {
      setMsg({ type: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    run(() => api.get("/profile/extras"));
  }, []);

  function onPick(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    run(() => api.post("/profile/photo", form), "Photo saved");
  }

  const link = extras?.slug ? `${window.location.origin}/u/${extras.slug}` : "";

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  if (!extras) return null;

  return (
    <section className="glass card wide">
      <h2>Photo and public profile</h2>

      <div className="row" style={{ gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
        {extras.photo_url ? (
          <img className="avatar-xl" src={(api.defaults.baseURL ?? "") + extras.photo_url} alt="Your photo" />
        ) : (
          <div className="avatar-xl avatar-empty">No photo</div>
        )}
        <div>
          <input
            ref={fileInput}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={onPick}
            style={{ display: "none" }}
          />
          <div className="actions">
            <button className="btn small primary-inline" disabled={busy} onClick={() => fileInput.current.click()}>
              {extras.photo_url ? "Change photo" : "Upload photo"}
            </button>
            {extras.photo_url && (
              <button className="btn small" disabled={busy} onClick={() => run(() => api.delete("/profile/photo"), "Photo removed")}>
                Remove
              </button>
            )}
          </div>
          <p className="muted small">JPG, PNG or WebP, up to 3 MB. It is cropped to a square.</p>
        </div>
      </div>

      <h4 className="sheet-title">Public profile</h4>
      <label className="note-pref" style={{ borderTop: 0, padding: 0 }}>
        <input
          type="checkbox"
          checked={extras.is_public}
          disabled={busy}
          onChange={(e) => run(() => api.put("/profile/public", { enabled: e.target.checked }))}
        />
        <span>Let anyone with my link see my profile</span>
      </label>
      <p className="muted small">
        It shows your name, photo, headline, location, bio, skills, experience, education and portfolio links.
        It never shows your email, phone, salary details or resumes, and search engines are told to skip it.
      </p>

      {extras.is_public && link && (
        <div className="save-row">
          <input readOnly value={link} />
          <button className="btn small" onClick={copy}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            className="btn small"
            disabled={busy}
            onClick={() => {
              if (window.confirm("Make a new link? The old link will stop working.")) {
                run(() => api.post("/profile/public/regenerate"), "New link created");
              }
            }}
          >
            New link
          </button>
        </div>
      )}
      {msg.text && <div className={msg.type === "error" ? "msg error" : "msg ok"}>{msg.text}</div>}
    </section>
  );
}