import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

const MESSAGES = {
  verified: "Your company is verified. Your jobs are visible to job seekers.",
  pending: "Your request is waiting for review. Your jobs go live once it is approved.",
  unverified: "Your company is not verified yet. Your jobs stay hidden until an admin verifies it.",
  rejected: "Your last request was rejected.",
};
const LABEL = {
  verified: "Verified",
  pending: "Pending",
  unverified: "Unverified",
  rejected: "Rejected",
};

export default function VerificationCard({ company }) {
  const [info, setInfo] = useState(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      const { data } = await api.get("/recruiter/company/verification");
      setInfo(data);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function request(e) {
    e.preventDefault();
    setError("");
    try {
      const { data } = await api.post("/recruiter/company/verification", { note: note.trim() });
      setInfo(data);
      setNote("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (!info) return error ? <div className="msg error">{error}</div> : null;

  const canRequest = info.status === "unverified" || info.status === "rejected";

  return (
    <section className="glass card">
      <div className="section-head">
        <div>
          <h2>Company verification</h2>
          <p className="muted">{MESSAGES[info.status]}</p>
        </div>
        <span className={`badge ${info.status}`}>{LABEL[info.status]}</span>
      </div>

      {info.note && info.status !== "verified" && (
        <div className="verify-note">
          <span className="muted small">{info.status === "rejected" ? "Reason" : "Your note"}</span>
          <div>{info.note}</div>
        </div>
      )}

      {error && <div className="msg error">{error}</div>}

      {canRequest && (
        <form onSubmit={request}>
          <label className="field">
            <span>How can we verify {company.name}?</span>
            <textarea
              rows="3"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={1000}
              placeholder="Official website, LinkedIn company page, registration number, your work email..."
              required
            />
          </label>
          <button className="btn primary">Request verification</button>
        </form>
      )}
    </section>
  );
}