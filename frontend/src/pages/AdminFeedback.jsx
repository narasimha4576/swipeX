import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { fromServer } from "../time";

const KINDS = [
  ["", "All"],
  ["feedback", "Feedback"],
  ["problem", "Problems"],
];
const STATUSES = [
  ["", "Any status"],
  ["new", "New"],
  ["reviewing", "Reviewing"],
  ["done", "Done"],
];

export default function AdminFeedback() {
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("");
  const [data, setData] = useState(null);
  const [notes, setNotes] = useState({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const params = {};
      if (kind) params.kind = kind;
      if (status) params.status = status;
      const { data: result } = await api.get("/admin/feedback", { params });
      setData(result);
      setNotes((old) => {
        const next = { ...old };
        result.items.forEach((item) => {
          if (!(item.id in next)) next[item.id] = item.admin_note ?? "";
        });
        return next;
      });
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [kind, status]);

  useEffect(() => {
    load();
  }, [load]);

  async function update(id, body) {
    setError("");
    try {
      await api.patch(`/admin/feedback/${id}`, body);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(id) {
    if (!window.confirm("Delete this message for good?")) return;
    setError("");
    try {
      await api.delete(`/admin/feedback/${id}`);
      load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (!data && !error) return <p className="muted">Loading...</p>;

  return (
    <>
      <section className="glass card">
        <h2>Feedback and problem reports</h2>
        <p className="muted">
          New: {data?.counts?.new ?? 0} | Reviewing: {data?.counts?.reviewing ?? 0} | Done: {data?.counts?.done ?? 0}.
          Names and emails show only when the person allowed contact.
        </p>
        <div className="chip-wrap">
          {KINDS.map(([value, label]) => (
            <button key={label} className={kind === value ? "fchip on" : "fchip"} onClick={() => setKind(value)}>
              {label}
            </button>
          ))}
        </div>
        <div className="chip-wrap" style={{ marginTop: "0.5rem" }}>
          {STATUSES.map(([value, label]) => (
            <button key={label} className={status === value ? "fchip on" : "fchip"} onClick={() => setStatus(value)}>
              {label}
            </button>
          ))}
        </div>
        {error && <div className="msg error">{error}</div>}
      </section>

      {data && data.items.length === 0 && (
        <section className="glass card">
          <p className="muted">Nothing here yet.</p>
        </section>
      )}

      {data?.items.map((item) => (
        <article className="glass card feedback-item" key={item.id}>
          <div className="row" style={{ gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
            <span className={item.kind === "problem" ? "badge closed" : "badge open"}>
              {item.kind === "problem" ? "Problem" : "Feedback"}
            </span>
            {item.rating && <span title={`${item.rating} of 5`}>{"★".repeat(item.rating) + "☆".repeat(5 - item.rating)}</span>}
            <span className="muted small">{fromServer(item.created_at).toLocaleString()}</span>
          </div>

          <p style={{ whiteSpace: "pre-wrap", margin: "0.7rem 0" }}>{item.message}</p>

          <div className="muted small">
            Page: {item.page ?? "-"} | Browser: {item.browser ?? "-"} | Reference: {item.error_ref ?? "-"}
          </div>
          <div className="muted small">
            From:{" "}
            {item.who
              ? `${item.who.name ? item.who.name + " " : ""}(${item.who.email})`
              : item.signed_in
                ? "a signed-in user (anonymous)"
                : "someone not signed in (anonymous)"}
          </div>

          <div className="save-row" style={{ marginTop: "0.8rem" }}>
            <select value={item.status} onChange={(e) => update(item.id, { status: e.target.value })} style={{ width: "auto" }}>
              <option value="new">New</option>
              <option value="reviewing">Reviewing</option>
              <option value="done">Done</option>
            </select>
            <input
              value={notes[item.id] ?? ""}
              onChange={(e) => setNotes({ ...notes, [item.id]: e.target.value })}
              placeholder="Private note for yourself"
              maxLength={1000}
            />
            <button className="btn small" onClick={() => update(item.id, { note: notes[item.id] ?? "" })}>
              Save note
            </button>
            <button className="btn small" onClick={() => remove(item.id)}>
              Delete
            </button>
          </div>
        </article>
      ))}
    </>
  );
}