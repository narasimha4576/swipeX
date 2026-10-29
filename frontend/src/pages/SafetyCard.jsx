import { useEffect, useState } from "react";
import api from "../api";

const LEVEL = {
  low: ["strong", "Looks fine"],
  medium: ["limited", "Be careful"],
  high: ["high", "High risk"],
};

const TIPS = [
  "A real employer never asks you to pay: no registration fee, training fee, deposit or equipment charge.",
  "Open the company's own website and check that the same job is on its careers page.",
  "Be careful if you can only reach them on WhatsApp or Telegram, or from a personal Gmail or Yahoo address.",
  "An offer letter without an interview is a red flag.",
  "A salary far above normal for a fresher is a warning sign.",
  "Search the company name with the word scam or reviews, and check it is a registered company.",
  "Never share Aadhaar, PAN, bank details or an OTP during the application.",
  "Apply through the company's official site or a verified link, never through a link sent in a chat.",
];

export default function SafetyCard({ jobId }) {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get(`/jobs/${jobId}/safety`)
      .then(({ data }) => {
        if (!cancelled) setInfo(data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  if (!info) return null;
  const [levelClass, levelText] = LEVEL[info.level];

  return (
    <div className={`safety ${info.level}`}>
      <div className="row between">
        <h4 className="sheet-title" style={{ margin: 0 }}>
          Safety check
        </h4>
        <span className={`level ${levelClass}`}>{levelText}</span>
      </div>

      {info.flags.length === 0 && (
        <p className="muted small">No warning signs were found in this posting.</p>
      )}
      {info.flags.map((flag, i) => (
        <div className="signal" key={"flag" + i}>
          <span className={`signal-icon ${flag.severity === "low" ? "unknown" : "no"}`}>!</span>
          <div>{flag.text}</div>
        </div>
      ))}
      {info.good.map((text, i) => (
        <div className="signal" key={"good" + i}>
          <span className="signal-icon ok">+</span>
          <div>{text}</div>
        </div>
      ))}

      <details className="tips">
        <summary>How to spot a fake job</summary>
        <ul>
          {TIPS.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}