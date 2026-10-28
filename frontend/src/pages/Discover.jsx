import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useMotionValue, useTransform } from "framer-motion";
import api, { errorMessage } from "../api";
import CompanyLink from "./CompanyLink";
import {
  COMP_LABEL,
  JOB_TYPE_LABEL,
  LEVEL_LABEL,
  TYPE_LABEL,
  logoColor,
  salary,
  timeAgo,
} from "../jobUtils";

function Svg({ children }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="28"
      height="28"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

const cardVariants = {
  exit: (x) => ({ x, opacity: 0, rotate: x / 25, transition: { duration: 0.25 } }),
};

function SwipeCard({ job, position, exitX, onSwipe }) {
  const isTop = position === 0;
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-220, 220], [-12, 12]);
  const saveOpacity = useTransform(x, [30, 130], [0, 1]);
  const skipOpacity = useTransform(x, [-130, -30], [1, 0]);

  return (
    <motion.div
      className="glass swipe-card"
      style={isTop ? { x, rotate, zIndex: 10 } : { zIndex: 10 - position }}
      drag={isTop ? "x" : false}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.9}
      onDragEnd={(_, info) => {
        const power = info.offset.x + info.velocity.x * 0.2;
        if (power > 140) onSwipe("right");
        else if (power < -140) onSwipe("left");
      }}
      initial={{ scale: 0.92, y: 24, opacity: 0 }}
      animate={{ scale: 1 - position * 0.05, y: position * 14, opacity: 1 }}
      custom={exitX}
      variants={cardVariants}
      exit="exit"
    >
      <motion.div className="stamp save" style={{ opacity: saveOpacity }}>
        SAVE
      </motion.div>
      <motion.div className="stamp skip" style={{ opacity: skipOpacity }}>
        SKIP
      </motion.div>

      <div className="job-top">
        <div className="logo" style={{ background: logoColor(job.company.name) }}>
          {job.company.name.charAt(0)}
        </div>
        <div className="job-title">
          <h3><Link className="title-link" onPointerDownCapture={(e) => e.stopPropagation()} to={"/jobs/" + job.id}>{job.title}</Link></h3>
          <CompanyLink company={job.company} />
        </div>
      </div>

      <div className="row" style={{ flexWrap: "wrap" }}>
        <span className={`badge ${job.company.company_type}`}>
          {TYPE_LABEL[job.company.company_type] ?? job.company.company_type}
        </span>
        <span className={`comp ${job.competition_level}`}>{COMP_LABEL[job.competition_level]}</span>
      </div>

      <div className="meta">
        <span>{job.is_remote ? "Remote" : job.location}</span>
        <span>{JOB_TYPE_LABEL[job.job_type] ?? job.job_type}</span>
        <span>{LEVEL_LABEL[job.experience_level] ?? job.experience_level}</span>
      </div>

      <div className="salary">{salary(job)}</div>

      <div className="chips">
        {job.skills.map((s) => (
          <span className="chip" key={s}>
            {s}
          </span>
        ))}
      </div>

      <p className="muted clamp">{job.description}</p>

      <div className="row between foot muted small">
        <span>Posted {timeAgo(job.created_at)}</span>
        <span>{job.source === "native" ? `${job.applicant_count} applicants` : "Official listing"}</span>
      </div>
    </motion.div>
  );
}

export default function Discover() {
  const [deck, setDeck] = useState([]);
  const [meta, setMeta] = useState({ remaining: 0, saved: 0, skipped: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exitX, setExitX] = useState(0);
  const [last, setLast] = useState(null);
  const seen = useRef(new Set());
  const locked = useRef(false);
  const queue = useRef(Promise.resolve());

  function enqueue(fn) {
    const p = queue.current.then(fn);
    queue.current = p.catch(() => {});
    return p;
  }

  async function fetchDeck(initial) {
    try {
      const { data } = await api.get("/swipes/deck", { params: { limit: 10 } });
      if (initial) {
        setMeta({ remaining: data.remaining, saved: data.saved, skipped: data.skipped });
      }
      setDeck((cur) => {
        const ids = new Set(cur.map((j) => j.id));
        return [
          ...cur,
          ...data.items.filter((j) => !ids.has(j.id) && !seen.current.has(j.id)),
        ];
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      if (initial) setLoading(false);
    }
  }

  useEffect(() => {
    fetchDeck(true);
  }, []);

  async function commit(direction) {
    const job = deck[0];
    if (!job || locked.current) return;
    locked.current = true;
    setTimeout(() => {
      locked.current = false;
    }, 250);

    const dSaved = direction === "right" ? 1 : 0;
    const dSkipped = direction === "left" ? 1 : 0;

    seen.current.add(job.id);
    setExitX(direction === "right" ? 500 : -500);
    setDeck((d) => d.slice(1));
    setLast({ job, direction });
    setMeta((m) => ({
      remaining: m.remaining - 1,
      saved: m.saved + dSaved,
      skipped: m.skipped + dSkipped,
    }));
    setError("");
    if (deck.length - 1 <= 2 && meta.remaining - 1 > deck.length - 1) fetchDeck(false);

    try {
      await enqueue(() => api.post("/swipes", { job_id: job.id, direction }));
    } catch (err) {
      setError(errorMessage(err));
      seen.current.delete(job.id);
      setDeck((d) => [job, ...d]);
      setMeta((m) => ({
        remaining: m.remaining + 1,
        saved: m.saved - dSaved,
        skipped: m.skipped - dSkipped,
      }));
      setLast(null);
    }
  }

  async function undo() {
    if (!last) return;
    const { job, direction } = last;
    setLast(null);
    try {
      await enqueue(() => api.delete(`/swipes/${job.id}`));
      seen.current.delete(job.id);
      setExitX(0);
      setDeck((d) => [job, ...d]);
      setMeta((m) => ({
        remaining: m.remaining + 1,
        saved: m.saved - (direction === "right" ? 1 : 0),
        skipped: m.skipped - (direction === "left" ? 1 : 0),
      }));
    } catch (err) {
      setError(errorMessage(err));
      setLast({ job, direction });
    }
  }

  useEffect(() => {
    function onKey(e) {
      if (e.repeat) return;
      if (e.key === "ArrowRight") commit("right");
      if (e.key === "ArrowLeft") commit("left");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const visible = deck.slice(0, 3);

  return (
    <section>
      <div className="section-head">
        <div>
          <h2>Discover</h2>
          <p className="muted">Swipe right to save, left to skip.</p>
          <div className="stats">
            <span className="stat">Saved {meta.saved}</span>
            <span className="stat">Skipped {meta.skipped}</span>
            <span className="stat">{meta.remaining} left</span>
          </div>
        </div>
      </div>

      {error && <div className="msg error">{error}</div>}
      {loading && <p className="muted">Loading jobs...</p>}

      <div className="swipe-stack">
        {!loading && deck.length === 0 && (
          <div className="empty-state glass card">
            <div>
              <h3>You are all caught up</h3>
              <p className="muted">
                You went through every opening. New jobs will appear here.
              </p>
              <Link className="btn small" to="/jobs">
                Browse all jobs
              </Link>
            </div>
          </div>
        )}
        <AnimatePresence custom={exitX}>
          {visible.map((job, i) => (
            <SwipeCard key={job.id} job={job} position={i} exitX={exitX} onSwipe={commit} />
          ))}
        </AnimatePresence>
      </div>

      <div className="swipe-actions">
        <button
          className="round-btn skip"
          onClick={() => commit("left")}
          disabled={!deck.length}
          aria-label="Skip"
        >
          <Svg>
            <path d="M6 6l12 12M18 6L6 18" />
          </Svg>
        </button>
        <button className="round-btn undo" onClick={undo} disabled={!last} aria-label="Undo">
          <Svg>
            <path d="M1 4v6h6" />
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
          </Svg>
        </button>
        <button
          className="round-btn save"
          onClick={() => commit("right")}
          disabled={!deck.length}
          aria-label="Save"
        >
          <Svg>
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </Svg>
        </button>
      </div>
      <p className="muted small center-text">Tip: you can also use the left and right arrow keys.</p>
    </section>
  );
}