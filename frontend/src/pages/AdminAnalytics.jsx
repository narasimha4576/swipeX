import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";

function BarChart({ data }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const width = 600;
  const height = 110;
  const gap = data.length > 45 ? 1 : 3;
  const bar = (width - gap * (data.length - 1)) / data.length;
  return (
    <svg viewBox={`0 0 ${width} ${height + 20}`} className="chart" role="img">
      {data.map((d, i) => {
        const h = (d.value / max) * height;
        return (
          <g key={d.date}>
            <title>{`${d.date}: ${d.value}`}</title>
            <rect x={i * (bar + gap)} y={height - Math.max(h, d.value ? 2 : 0)} width={bar} height={Math.max(h, d.value ? 2 : 0)} fill="currentColor" />
          </g>
        );
      })}
      <line x1="0" x2={width} y1={height + 0.5} y2={height + 0.5} stroke="currentColor" strokeOpacity="0.3" />
      <text x="0" y={height + 15}>
        {data[0]?.date}
      </text>
      <text x={width} y={height + 15} textAnchor="end">
        {data[data.length - 1]?.date}
      </text>
    </svg>
  );
}

function ChartCard({ title, data }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  return (
    <div className="stat">
      <div className="muted small">{title}</div>
      <div className="stat-num">{total}</div>
      <BarChart data={data} />
    </div>
  );
}

function Pairs({ rows, empty }) {
  if (!rows.length) return <p className="muted small">{empty}</p>;
  const max = Math.max(...rows.map((r) => r[1]));
  return (
    <div>
      {rows.map(([name, count]) => (
        <div className="bar-row" key={name}>
          <span className="bar-name">{name}</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${Math.max(3, (100 * count) / max)}%` }} />
          </span>
          <span className="bar-count">{count}</span>
        </div>
      ))}
    </div>
  );
}

export default function AdminAnalytics() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .get("/admin/analytics", { params: { days } })
      .then(({ data }) => {
        if (!cancelled) {
          setData(data);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  if (error) return <div className="msg error">{error}</div>;
  if (!data) return <p className="muted">Loading...</p>;

  const r = data.responses;

  return (
    <>
      <section className="glass card">
        <div className="section-head">
          <div>
            <h2>Analytics</h2>
            <p className="muted">
              Counts only. No names, emails or profile contents. SwipeX does not track visits, so the funnel starts at
              signup.
            </p>
          </div>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ width: "auto" }}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
        <div className="stat-grid chart-grid">
          <ChartCard title="New job seekers" data={data.series.seekers} />
          <ChartCard title="New recruiters" data={data.series.recruiters} />
          <ChartCard title="Applications sent" data={data.series.applications} />
          <ChartCard title="Jobs liked" data={data.series.likes} />
        </div>
      </section>

      <section className="glass card">
        <h3>Job seeker funnel (all time)</h3>
        <p className="muted small">
          Each line is the number of people who did that. A person can skip a step, so lines are not strictly nested.
        </p>
        {data.funnel.map((step) => (
          <div className="funnel-row" key={step.key}>
            <div className="funnel-label">{step.label}</div>
            <div className="funnel-track">
              <div className="funnel-fill" style={{ width: `${Math.max(step.percent, step.count ? 2 : 0)}%` }} />
            </div>
            <div className="funnel-num">
              {step.count} <span className="muted small">({step.percent}%)</span>
            </div>
          </div>
        ))}
      </section>

      <section className="glass card">
        <h3>Hiring responses</h3>
        <div className="stat-grid">
          <div className="stat">
            <div className="muted small">Applications</div>
            <div className="stat-num">{r.applications}</div>
          </div>
          <div className="stat">
            <div className="muted small">Answered by a recruiter</div>
            <div className="stat-num">{r.answered_percent}%</div>
            <div className="muted small">{r.answered} of {r.applications}</div>
          </div>
          <div className="stat">
            <div className="muted small">Average time to first answer</div>
            <div className="stat-num">{r.average_hours === null ? "-" : `${r.average_hours} h`}</div>
          </div>
        </div>
      </section>

      <section className="glass card">
        <h3>Skills: what people have and what jobs ask for</h3>
        <div className="two-col">
          <div>
            <h4 className="sheet-title">People ({data.min_group}+ with the skill)</h4>
            <Pairs rows={data.people_skills} empty="Not enough profiles yet. A skill appears once 3 people list it." />
          </div>
          <div>
            <h4 className="sheet-title">Open jobs</h4>
            <Pairs rows={data.job_skills} empty="No open jobs with skills yet." />
          </div>
        </div>
      </section>

      <section className="glass card">
        <h3>Most applied</h3>
        <div className="two-col">
          <div>
            <h4 className="sheet-title">Jobs</h4>
            {data.top_jobs.length === 0 && <p className="muted small">No applications yet.</p>}
            {data.top_jobs.map((j, i) => (
              <div className="bar-row" key={i}>
                <span className="bar-name">
                  {j.title} <span className="muted small">at {j.company}</span>
                </span>
                <span className="bar-count">{j.applications}</span>
              </div>
            ))}
          </div>
          <div>
            <h4 className="sheet-title">Companies</h4>
            <Pairs rows={data.top_companies.map((c) => [c.company, c.applications])} empty="No applications yet." />
          </div>
        </div>
      </section>

      <section className="glass card">
        <h3>Jobs ({data.jobs.open} open)</h3>
        <div className="two-col">
          <div>
            <h4 className="sheet-title">By source</h4>
            <Pairs rows={data.jobs.by_source} empty="No jobs." />
          </div>
          <div>
            <h4 className="sheet-title">By country</h4>
            <Pairs rows={data.jobs.by_country} empty="No country information yet." />
          </div>
        </div>
      </section>
    </>
  );
}