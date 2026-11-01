import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { timeAgo } from "../jobUtils";

const POLL_MS = 60000;

export default function NotificationBell() {
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const box = useRef(null);

  async function refreshCount() {
    try {
      const { data } = await api.get("/notifications/unread-count");
      setUnread(data.unread);
    } catch {
      // A failed check is ignored. The next one tries again.
    }
  }

  useEffect(() => {
    refreshCount();
    const timer = setInterval(() => {
      if (!document.hidden) refreshCount();
    }, POLL_MS);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onClick(event) {
      if (box.current && !box.current.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (!next) return;
    try {
      const { data } = await api.get("/notifications");
      setItems(data.items);
      setUnread(data.unread);
    } catch {
      setItems([]);
    }
  }

  async function openItem(item) {
    setOpen(false);
    if (!item.is_read) {
      try {
        await api.post(`/notifications/${item.id}/read`);
        setUnread((n) => Math.max(0, n - 1));
      } catch {
        // Ignored. The notification stays unread.
      }
    }
    if (item.link) navigate(item.link);
  }

  async function readAll() {
    try {
      await api.post("/notifications/read-all");
      setItems((list) => list.map((n) => ({ ...n, is_read: true })));
      setUnread(0);
    } catch {
      // Ignored.
    }
  }

  return (
    <div className="bell-wrap" ref={box}>
      <button className="bell-btn" onClick={toggle} aria-label="Notifications">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {unread > 0 && <span className="bell-count">{unread > 9 ? "9+" : unread}</span>}
      </button>

      {open && (
        <div className="bell-panel">
          <div className="row between bell-head">
            <strong>Notifications</strong>
            {unread > 0 && (
              <button className="btn small" onClick={readAll}>
                Mark all read
              </button>
            )}
          </div>
          {items.length === 0 && (
            <p className="muted small" style={{ padding: "0.8rem" }}>
              Nothing yet. Save a search on the Jobs page and new matches will show up here.
            </p>
          )}
          {items.map((item) => (
            <button
              key={item.id}
              className={"note-item" + (item.is_read ? "" : " unread")}
              onClick={() => openItem(item)}
            >
              <strong>{item.title}</strong>
              {item.body && <div className="muted small">{item.body}</div>}
              <div className="muted small">{timeAgo(item.created_at)}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}