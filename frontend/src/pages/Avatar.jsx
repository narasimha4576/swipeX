import { useEffect, useState } from "react";
import api from "../api";

export default function Avatar({ user }) {
  const [url, setUrl] = useState(null);

  async function load() {
    if (user.role !== "job_seeker") return;
    try {
      const { data } = await api.get("/profile/extras");
      setUrl(data.photo_url ? (api.defaults.baseURL ?? "") + data.photo_url : null);
    } catch {
      setUrl(null);
    }
  }

  useEffect(() => {
    load();
    window.addEventListener("swipex-photo", load);
    return () => window.removeEventListener("swipex-photo", load);
  }, [user.id]);

  if (url) return <img className="avatar avatar-img" src={url} alt="" />;
  return <span className="avatar">{user.full_name.trim().charAt(0).toUpperCase()}</span>;
}