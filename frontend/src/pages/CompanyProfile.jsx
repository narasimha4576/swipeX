import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import CompanyLink from "./CompanyLink";
import OtherPortals from "./OtherPortals";
import { JOB_TYPE_LABEL, TYPE_LABEL, logoColor, timeAgo } from "../jobUtils";

const LEVEL = {
  strong: "Strong evidence",
  good: "Good evidence",
  limited: "Limited evidence",
};

function dateText(iso) {
  return iso ? iso.slice(0, 10) : "";
}

export default function CompanyProfile({ kind }) {
  const params = useParams();
  const navigate = useNavigate();
  const base = kind === "public" ? `/explore/public/${params.qid}` : `/explore/company/${params.id}`;

  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setSummary(null);
    setError("");
    api
      .get(base)
      .then(({ data }) => {
        if (!cancelled) setData(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [base]);

  async function makeSummary() {
    setBusy(true);
    setSummaryError("");
    try {
      const { data } = await api.post(`${base}/summary`);
      setSummary(data);
    } catch (err) {
      setSummaryError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function goBack() {
    if (window.history.length > 1) navigate(-1);
    else navigate("/companies");
  }

  if (!data) {
    return (
      <div className="detail-page">
        <button className="btn small" style={{ alignSelf: "flex-start" }} onClick={goBack}>
          Back
        </button>
        {error ? <div className="msg error">{error}</div> : <p className="muted">Looking up the company...</p>}
      </div>
    );
  }

  const facts = data.facts;
  const factItems = [
    ["Founded", facts.founded_year],
    ["Employees", facts.employees ? facts.employees.toLocaleString("en-IN") : null],
    ["Headquarters", facts.headquarters],
  ].filter(([, value]) => value);
  const q = encodeURIComponent(data.name);

  return (
    <div className="detail-page">
      <button className="btn small" style={{ alignSelf: "flex-start" }} onClick={goBack}>
        Back
      </button>

      <section className="glass card">
        <div className="job-top">
          {facts.logo_url ? (<img className="company-logo" src={facts.logo_url} alt="" referrerPolicy="no-referrer" />) : (<div className="logo">{data.name.charAt(0)}</div>)}
          <div className="job-title">
            <h1 className="detail-title" style={{ margin: 0 }}>
              {data.name}
            </h1>
            <div className="row" style={{ marginTop: "0.5rem", flexWrap: "wrap" }}>
              {data.company && (
                <>
                  <span className={`badge ${data.company.company_type}`}>
                    {TYPE_LABEL[data.company.company_type] ?? data.company.company_type}
                  </span>
                  <span className={`badge ${data.company.verification_status}`}>
                    {data.company.verification_status}
                  </span>
                </>
              )}
              {data.kind === "public" && <span className="badge other">Public record</span>}
              {data.trust_level && <span className={`level ${data.trust_level}`}>{LEVEL[data.trust_level]}</span>}
            </div>
          </div>
        </div>

        {data.description && <p className="muted" style={{ marginTop: "1rem" }}>{data.description}</p>}
        {facts.image_url && <img className="company-photo" src={facts.image_url} alt={data.name} loading="lazy" referrerPolicy="no-referrer" />}

        {factItems.length > 0 && (
          <div className="facts" style={{ marginTop: "1rem" }}>
            {factItems.map(([label, value]) => (
              <div className="fact" key={label}>
                <span className="muted small">{label}</span>
                <div>{value}</div>
              </div>
            ))}
          </div>
        )}

        <div className="actions" style={{ marginTop: "1rem" }}>
          {facts.website && (
            <a className="link" href={facts.website} target="_blank" rel="noreferrer">
              Website
            </a>
          )}
          {facts.wikipedia_url && (
            <a className="link" href={facts.wikipedia_url} target="_blank" rel="noreferrer">
              Wikipedia
            </a>
          )}
          {facts.wikidata_url && (
            <a className="link" href={facts.wikidata_url} target="_blank" rel="noreferrer">
              Wikidata record
            </a>
          )}
          <a
            className="link"
            href={"https://www.linkedin.com/search/results/companies/?keywords=" + q}
            target="_blank"
            rel="noreferrer"
          >
            Find on LinkedIn
          </a>
          <a
            className="link"
            href={"https://www.linkedin.com/search/results/content/?keywords=" + q}
            target="_blank"
            rel="noreferrer"
          >
            Their posts on LinkedIn
          </a>
        </div>

        {data.company && (
          <div style={{ marginTop: "1rem" }}>
            <span className="muted small">Verification details: </span>
            <CompanyLink company={data.company} />
          </div>
        )}
        {data.kind === "public" && !data.swipex_company_id && (
          <p className="muted small" style={{ marginTop: "1rem" }}>
            This company has no jobs on SwipeX yet. Public facts come from Wikidata and may be
            incomplete, so double-check on the company's own website.
          </p>
        )}
        {data.kind === "public" && data.swipex_company_id && (
          <p style={{ marginTop: "1rem" }}>
            <Link className="link" to={"/companies/" + data.swipex_company_id}>
              Open its SwipeX page
            </Link>
          </p>
        )}
      </section>

      <section className="glass card">
        <h2>Open jobs on SwipeX</h2>
        {data.jobs.length === 0 && <p className="muted">No open jobs on SwipeX right now.</p>}
        {data.jobs.map((job) => (
          <div className="job-row" key={job.id}>
            <div>
              <Link className="title-link" to={"/jobs/" + job.id}>
                <strong>{job.title}</strong>
              </Link>
              <div className="muted small">
                {job.is_remote ? "Remote" : job.location} | {JOB_TYPE_LABEL[job.job_type] ?? job.job_type}
              </div>
            </div>
            <span className="muted small">{timeAgo(job.created_at)}</span>
          </div>
        ))}
      </section>

      <section className="glass card">
        <h2>Recent news</h2>
        {data.news.length === 0 && <p className="muted">No recent news found.</p>}
        {data.news.map((item) => (
          <a className="news-item" key={item.link} href={item.link} target="_blank" rel="noreferrer">
            <div className="news-title">{item.title}</div>
            <div className="muted small">
              {[item.source, dateText(item.published_at)].filter(Boolean).join("  |  ")}
            </div>
          </a>
        ))}
        <p className="muted small" style={{ marginTop: "0.8rem" }}>
          Headlines come from a public news feed and open the original article.
        </p>
      </section>

      <section className="glass card ai-card">
        <div className="section-head" style={{ marginBottom: "0.6rem" }}>
          <div>
            <h2>AI summary</h2>
            <p className="muted small">Built only from the facts, jobs and headlines on this page.</p>
          </div>
          {!summary && (
            <button className="btn small primary-inline" onClick={makeSummary} disabled={busy}>
              {busy ? "Thinking..." : "Generate summary"}
            </button>
          )}
        </div>
        {summaryError && <div className="msg error">{summaryError}</div>}
        {!data.ai_available && !summary && (
          <p className="muted small">
            The AI is not set up yet. Add your key to backend/.env to switch this on.
          </p>
        )}
        {summary && (
          <>
            {summary.about && <p>{summary.about}</p>}
            {summary.recent.length > 0 && (
              <>
                <h4 className="sheet-title">Recent developments</h4>
                <ul>
                  {summary.recent.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </>
            )}
            {summary.hiring && (
              <>
                <h4 className="sheet-title">Hiring</h4>
                <p>{summary.hiring}</p>
              </>
            )}
            {summary.check_before_applying.length > 0 && (
              <>
                <h4 className="sheet-title">Check before applying</h4>
                <ul>
                  {summary.check_before_applying.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="muted ai-note">AI can make mistakes. Verify important details yourself.</p>
          </>
        )}
      </section>

      <Link className="glass card web-cta" to={"/companies/web?name=" + encodeURIComponent(data.name)}><strong>More from the web</strong><div className="muted small">Photos, videos, web results and live job boards</div></Link>

      <OtherPortals query={data.name} location="" />
    </div>
  );
}