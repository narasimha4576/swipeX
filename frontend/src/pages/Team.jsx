import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

export default function Team() {
  const [team, setTeam] = useState(null);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");
  const [copied, setCopied] = useState(false);

  async function run(call) {
    setMsg("");
    try {
      const { data } = await call();
      setTeam(data);
      setCode("");
    } catch (err) {
      setMsg(errorMessage(err));
    }
  }

  useEffect(() => {
    run(() => api.get("/recruiter/team"));
  }, []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(team.invite_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  if (!team) return <p className="muted">{msg || "Loading team..."}</p>;

  if (!team.company_name) {
    return (
      <section className="glass card">
        <h2>Join a company</h2>
        <p className="muted">
          If a colleague already set up your company on SwipeX, ask them for the invite code. Otherwise set up
          your own company in Workspace.
        </p>
        <div className="save-row">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Invite code, for example A3F9C21B"
            maxLength={20}
          />
          <button
            className="btn small primary-inline"
            disabled={code.trim().length < 4}
            onClick={() => run(() => api.post("/recruiter/team/join", { code: code.trim() }))}
          >
            Join
          </button>
        </div>
        {msg && <div className="msg error">{msg}</div>}
      </section>
    );
  }

  return (
    <section className="glass card">
      <h2>{team.company_name} team</h2>
      <p className="muted">
        Everyone on the team can post jobs, edit them, review applicants and shortlist.
      </p>

      {team.members.map((m) => (
        <div className="job-row" key={m.user_id}>
          <div>
            <strong>
              {m.full_name}
              {m.is_me ? " (you)" : ""}
            </strong>
            <div className="muted small">{m.email}</div>
          </div>
          <span className="actions">
            {m.is_owner && <span className="badge open">Owner</span>}
            {team.is_owner && !m.is_me && (
              <button
                className="btn small"
                onClick={() => {
                  if (window.confirm(`Remove ${m.full_name} from the team?`)) {
                    run(() => api.delete(`/recruiter/team/members/${m.user_id}`));
                  }
                }}
              >
                Remove
              </button>
            )}
          </span>
        </div>
      ))}

      {team.is_owner && team.invite_code && (
        <>
          <h4 className="sheet-title">Invite code</h4>
          <div className="save-row">
            <input readOnly value={team.invite_code} />
            <button className="btn small" onClick={copy}>
              {copied ? "Copied" : "Copy"}
            </button>
            <button className="btn small" onClick={() => run(() => api.post("/recruiter/team/regenerate"))}>
              New code
            </button>
          </div>
          <p className="muted small">
            Share it only with colleagues. Anyone with this code can post jobs and see applicants for your
            company. If it leaks, press New code and the old one stops working.
          </p>
        </>
      )}

      {!team.is_owner && (
        <div className="actions" style={{ marginTop: "1rem" }}>
          <button
            className="btn small"
            onClick={() => {
              if (window.confirm("Leave this company's team?")) run(() => api.post("/recruiter/team/leave"));
            }}
          >
            Leave team
          </button>
        </div>
      )}
      {msg && <div className="msg error">{msg}</div>}
    </section>
  );
}