import { useCallback, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import api from "../api";

export default function RecoveryNudge() {
  const [needed, setNeeded] = useState(false);

  const check = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/recovery");
      setNeeded(!data.created);
    } catch {
      setNeeded(false);
    }
  }, []);

  useEffect(() => {
    check();
    window.addEventListener("swipex-recovery", check);
    return () => window.removeEventListener("swipex-recovery", check);
  }, [check]);

  if (!needed) return null;
  return (
    <NavLink className="nudge" to="/account" title="Save recovery codes so you can reset your password">
      Save recovery codes
    </NavLink>
  );
}