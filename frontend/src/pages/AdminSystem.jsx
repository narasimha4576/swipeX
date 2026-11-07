import { Fragment, useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { fromServer } from "../time";

function Card({ title, children }) {
  return (
    <div className="stat">
      <div className="muted small">{title}</div>
      {children}
    </div>
  );
}

const when = (value) => (value ? fromServer(value).toLocaleString() : "never");

export default function AdminSystem() {
  const [system, setSystem] = useState(null);
  const [errors, setErrors] = useState([]);
  const [open, setOpen] = useState(null);
  const [detail, setDetail] = useState(null);
  const [note, setNote] = useState("");
  const [failed, setFailed] = useState("");

  async function load() {
    try {
      const [s, e] = await Promise.all([
        api.get("/admin/system"),
        api.get("/admin/errors", { params: { days: 7 } }),
      ]);
      setSystem(s.data);
      setErrors(e.data);
      setFailed("");
    } catch (err) {
      setFailed(errorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function show(fingerprint) {
    if (open === fingerprint) {
      setOpen(null);
      return;
    }
    setOpen(fingerprint);
    setDetail(null);
    try {
      const { data } = await api.get(`/admin/errors/${fingerprint}`);
      setDetail(data);
    } catch (err) {
      setNote(errorMessage(err));
    }
  }

  async function testError() {
    setNote("");
    try {
      await api.post("/admin/test-error");
      setNote("The test did not fail. Is this a production server?");
    } catch (err) {
      setNote("As planned, the website crashed on purpose: " + errorMessage(err));
    }
    load();
  }

  async function clearAll() {
    if (!window.confirm("Delete all saved errors?")) return;
    try {
      await api.post("/admin/errors/clear");
      setNote("Errors cleared.");
    } catch (err) {
      setNote(errorMessage(err));
    }
    load();
  }

  if (failed) return <div className="msg error">{failed}</div>;
  if (!system) return <p className="muted">Loading...</p>;

  const workerOk = system.worker.status === "ok";

  return (
    <>
      <section className="glass card">
        <h2>System</h2>
        <p className="muted">Is everything alive? Reload the page to refresh.</p>
        <div className="stat-grid">
          <Card title="Database">
            <div className="stat-num ok-text">OK</div>
            <div className="muted small">
              {system.database.latency_ms} ms | version {system.database.schema_version ?? "unknown"}
            </div>
          </Card>
          <Card title="Background worker">
            <div className={"stat-num " + (workerOk ? "ok-text" : "bad-text")}>
              {workerOk ? "Running" : system.worker.status === "stale" ? "Stopped?" : "Not seen"}
            </div>
            <div className="muted small">
              {system.worker.seconds === null ? "No sign of life yet" : `last sign of life ${system.worker.seconds}s ago`}
            </div>
          </Card>
          <Card title="Last job import">
            <div className="stat-num" style={{ fontSize: "1rem" }}>
              {system.last_import ? when(system.last_import.at) : "never"}
            </div>
            <div className="muted small">
              {system.last_import
                ? Object.entries(system.last_import.summary)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" | ") || "no numbers recorded"
                : ""}
            </div>
          </Card>
          <Card title="Free disk space (uploads)">
            <div className={"stat-num " + (system.uploads.free_mb !== null && system.uploads.free_mb < 500 ? "bad-text" : "")}>
              {system.uploads.free_mb ?? "?"} MB
            </div>
          </Card>
          <Card title="AI helper">
            <div className={"stat-num " + (system.ai_configured ? "ok-text" : "bad-text")}>
              {system.ai_configured ? "Set up" : "Not set up"}
            </div>
          </Card>
          <Card title="Errors">
            <div className={"stat-num " + (system.errors_24h ? "bad-text" : "ok-text")}>{system.errors_24h}</div>
            <div className="muted small">last 24 hours ({system.errors_7d} in 7 days)</div>
          </Card>
          <Card title="Server">
            <div className="muted small">
              {system.environment} | Python {system.python} | up {system.uptime_minutes} min
            </div>
          </Card>
        </div>
      </section>

      <section className="glass card">
        <div className="section-head">
          <div>
            <h3>Errors (last 7 days)</h3>
            <p className="muted small">The same error is grouped into one line. Nothing personal is saved.</p>
          </div>
          <div className="actions">
            {system.environment !== "production" && (<button className="btn small" onClick={testError}>Create a test error</button>)}
            <button className="btn small" onClick={clearAll} disabled={errors.length === 0}>
              Clear all
            </button>
          </div>
        </div>
        {note && <div className="msg ok">{note}</div>}
        {errors.length === 0 && <p className="muted">No errors. Good.</p>}
        {errors.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Last seen</th>
                  <th>Times</th>
                  <th>Type</th>
                  <th>Message</th>
                  <th>Where</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((e) => (
                  <Fragment key={e.fingerprint}>
                    <tr onClick={() => show(e.fingerprint)} style={{ cursor: "pointer" }}>
                      <td>{when(e.last_seen)}</td>
                      <td>{e.count}</td>
                      <td>{e.kind}</td>
                      <td>{e.message}</td>
                      <td>
                        {e.source} {e.method} {e.path}
                      </td>
                    </tr>
                    {open === e.fingerprint && (
                      <tr key={e.fingerprint + "-detail"}>
                        <td colSpan={5}>
                          {!detail && <span className="muted">Loading...</span>}
                          {detail && (
                            <>
                              <pre style={{ whiteSpace: "pre-wrap", overflowX: "auto", margin: 0 }}>{detail.trace}</pre>
                              <p className="muted small">
                                Reference codes:{" "}
                                {detail.occurrences.map((o) => `${o.error_id} (${when(o.at)})`).join(", ")}
                              </p>
                            </>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}