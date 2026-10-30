import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import OtherPortals from "./OtherPortals";
import { JOB_TYPE_LABEL, timeAgo } from "../jobUtils";

function dateText(iso) {
  return iso ? iso.slice(0, 10) : "";
}

export default function CompanyWeb() {
  const [params] = useSearchParams();
  const name = (params.get("name") || "").trim();
  const navigate = useNavigate();
  const q = encodeURIComponent(name);

  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [playing, setPlaying] = useState(null);
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (name.length < 2) return;
    let cancelled = false;
    setData(null);
    setSummary(null);
    setError("");
    setPlaying(null);
    api
      .get("/explore/web", { params: { name } })
      .then(({ data }) => {
        if (!cancelled) setData(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  async function makeSummary() {
    setBusy(true);
    setSummaryError("");
    try {
      const { data } = await api.post("/explore/web/summary", null, { params: { name } });
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

  const quick = [
    ["Google Images", "https://www.google.com/search?tbm=isch&q=" + q + "+company"],
    ["YouTube", "https://www.youtube.com/results?search_query=" + q + "+company"],
    ["LinkedIn page", "https://www.linkedin.com/search/results/companies/?keywords=" + q],
    ["LinkedIn posts", "https://www.linkedin.com/search/results/content/?keywords=" + q],
    ["Reviews", "https://www.google.com/search?q=" + q + "+company+reviews"],
    ["Careers page", "https://www.google.com/search?q=" + q + "+careers"],
  ];

  return (
    <div className="detail-page">
      <button className="btn small" style={{ alignSelf: "flex-start" }} onClick={goBack}>
        Back
      </button>

      <section className="glass card">
        <h1 className="detail-title" style={{ marginTop: 0 }}>
          {name}
        </h1>
        <p className="muted small">
          Everything we could find on the web for this name. Check that it is the company you mean.
        </p>
        <div className="actions">
          {quick.map(([label, url]) => (
            <a key={label} className="btn small" href={url} target="_blank" rel="noreferrer">
              {label}
            </a>
          ))}
        </div>
      </section>

      {!data && !error && (
        <p className="muted">Searching the web for {name}. This can take up to half a minute...</p>
      )}
      {error && <div className="msg error">{error}</div>}

      {data && (
        <>
          <section className="glass card">
            <h2>Jobs</h2>
            {data.swipex_jobs.length > 0 && <h4 className="sheet-title">On SwipeX</h4>}
            {data.swipex_jobs.map((job) => (
              <div className="job-row" key={"s" + job.id}>
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

            {data.live_jobs.length > 0 && (
              <>
                <h4 className="sheet-title">Live on the company's job board</h4>
                {data.live_jobs.map((job) => (
                  <div className="job-row" key={job.url}>
                    <div>
                      <a className="title-link" href={job.url} target="_blank" rel="noreferrer">
                        <strong>{job.title}</strong>
                      </a>
                      <div className="muted small">
                        {job.location || "Location not listed"} | {JOB_TYPE_LABEL[job.job_type] ?? job.job_type} |{" "}
                        {job.source}
                      </div>
                    </div>
                    <span className="muted small">{dateText(job.posted)}</span>
                  </div>
                ))}
                <p className="muted small" style={{ marginTop: "0.8rem" }}>
                  Found by matching the company name to a job board:{" "}
                  <a className="link" href={data.live_jobs[0].board_url} target="_blank" rel="noreferrer">
                    open the board
                  </a>{" "}
                  to confirm it is the right company.
                </p>
              </>
            )}

            {data.swipex_jobs.length === 0 && data.live_jobs.length === 0 && (
              <p className="muted">
                No open jobs found on Greenhouse, Lever or Ashby for this name. The company may use
                another system, so try the careers page button above.
              </p>
            )}
          </section>

          <section className="glass card">
            <h2>Photos</h2>
            {data.images.length === 0 && (
              <p className="muted">No photos found here. Try the Google Images button above.</p>
            )}
            <div className="photo-grid">
              {data.images.map((url) => (
                <a key={url} href={url} target="_blank" rel="noreferrer">
                  <img src={url} alt="" loading="lazy" referrerPolicy="no-referrer" />
                </a>
              ))}
            </div>
          </section>

          <section className="glass card">
            <h2>Videos</h2>
            {!data.videos_enabled && (
              <p className="muted small">
                Add a free YouTube key to backend/.env to see videos here. Until then, use the YouTube
                button above.
              </p>
            )}
            {data.videos_enabled && data.videos.length === 0 && <p className="muted">No videos found.</p>}
            <div className="video-grid">
              {data.videos.map((video) => (
                <div key={video.id}>
                  {playing === video.id ? (
                    <iframe
                      className="video-frame"
                      src={"https://www.youtube-nocookie.com/embed/" + video.id + "?autoplay=1"}
                      title={video.title}
                      allow="autoplay; encrypted-media; picture-in-picture"
                      allowFullScreen
                    />
                  ) : (
                    <button className="video-thumb" onClick={() => setPlaying(video.id)}>
                      <img src={video.thumbnail} alt="" loading="lazy" />
                    </button>
                  )}
                  <div className="news-title">{video.title}</div>
                  <div className="muted small">{video.channel}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="glass card">
            <h2>Web results</h2>
            {data.results.length === 0 && (
              <p className="muted">No web results right now (the free search may be busy). Try again in a minute.</p>
            )}
            {data.results.map((item) => (
              <a className="news-item" key={item.url} href={item.url} target="_blank" rel="noreferrer">
                <div className="news-title">{item.title}</div>
                <div className="muted small">{item.snippet}</div>
              </a>
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
          </section>

          <section className="glass card ai-card">
            <div className="section-head" style={{ marginBottom: "0.6rem" }}>
              <div>
                <h2>AI summary</h2>
                <p className="muted small">Built only from the jobs, web results and headlines on this page.</p>
              </div>
              {!summary && (
                <button className="btn small primary-inline" onClick={makeSummary} disabled={busy}>
                  {busy ? "Thinking..." : "Generate summary"}
                </button>
              )}
            </div>
            {summaryError && <div className="msg error">{summaryError}</div>}
            {summary && (
              <>
                {summary.about && <p>{summary.about}</p>}
                {summary.recent.length > 0 && (
                  <ul>
                    {summary.recent.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                )}
                {summary.hiring && <p>{summary.hiring}</p>}
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

          <OtherPortals query={name} location="" />
        </>
      )}
    </div>
  );
}