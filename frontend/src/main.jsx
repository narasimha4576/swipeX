import ErrorBoundary from "./pages/ErrorBoundary";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "./tilt.js";
import App from "./App.jsx";
import api from "./api";
api.get("/health").catch(() => {});

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ErrorBoundary><App /></ErrorBoundary>
  </StrictMode>
);