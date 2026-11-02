import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api";

export default function PublicProfile() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => document.head.removeChild(meta);
  }, []);

  useEffect(() => {
    api
      .get(`/public/profiles/${slug}`)
      .then(({ data }) => setData(data))
      .catch(() => setError("This profile is not available."));
  }, [slug]);

  return (
    <div className="public-wrap">
      <div className="brand" style={{ marginBottom: "1rem" }}>
        Swipe<span className="accent">X</span>
      </div>

      {error && (
        <section className="glass card">
          <h2>Profile not found</h2>
          <p className="muted">{error}</p>
        </section>
      )}

      {!data && !error && <p className="muted">Loading...</p>}

      {data && (
        <>
          <section className="glass card">
            <div className="row" style={{ gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
              {data.photo_url ? (
                <img className="avatar-xl" src={(api.defaults.baseURL ?? "") + data.photo_url} alt="" />
              ) : (
                <div className="avatar-xl avatar-empty">{data.full_name.charAt(0)}</div>
              )}
              <div>
                <h1 style={{ margin: 0 }}>{data.full_name}</h1>
                {data.headline && <div>{data.headline}</div>}
                <div className="muted small">
                  {[data.location, `${data.experience_years} yrs experience`].filter(Boolean).join("  |  ")}
                </div>
              </div>
            </div>
            {data.bio && <p style={{ marginTop: "1rem" }}>{data.bio}</p>}
            {data.skills.length > 0 && (
              <div className="chips">
                {data.skills.map((s) => (
                  <span className="chip" key={s}>
                    {s}
                  </span>
                ))}
              </div>
            )}
          </section>

          {data.experiences.length > 0 && (
            <section className="glass card">
              <h2>Experience</h2>
              {data.experiences.map((x) => (
                <div className="item" key={x.id}>
                  <div>
                    <h3>{x.title}</h3>
                    <div className="muted small">
                      {x.company} | {x.start_year} - {x.end_year ?? "Present"}
                    </div>
                    {x.description && <div>{x.description}</div>}
                  </div>
                </div>
              ))}
            </section>
          )}

          {data.educations.length > 0 && (
            <section className="glass card">
              <h2>Education</h2>
              {data.educations.map((x) => (
                <div className="item" key={x.id}>
                  <div>
                    <h3>
                      {x.degree}
                      {x.field_of_study ? `, ${x.field_of_study}` : ""}
                    </h3>
                    <div className="muted small">
                      {x.school} | {x.start_year} - {x.end_year ?? "Present"}
                      {x.grade ? ` | ${x.grade}` : ""}
                    </div>
                  </div>
                </div>
              ))}
            </section>
          )}

          {data.portfolio.length > 0 && (
            <section className="glass card">
              <h2>Portfolio</h2>
              {data.portfolio.map((p) => (
                <div key={p.id}>
                  <a className="link" href={p.url} target="_blank" rel="noopener noreferrer">
                    {p.title}
                  </a>
                  {p.description && <div className="muted small">{p.description}</div>}
                </div>
              ))}
            </section>
          )}
        </>
      )}
    </div>
  );
}