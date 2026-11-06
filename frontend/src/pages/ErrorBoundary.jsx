import { Component } from "react";
import api from "../api";

export default class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    try {
      api
        .post("/errors/client", {
          message: String(error?.message ?? error).slice(0, 300),
          stack: String(info?.componentStack ?? error?.stack ?? "").slice(0, 3000),
          page: window.location.pathname,
        })
        .catch(() => {});
    } catch {
      // Reporting is best effort. The person still sees the friendly page.
    }
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="public-wrap">
        <section className="glass card">
          <h2>Something went wrong</h2>
          <p className="muted">This page hit a problem. It has been reported. Please reload, or go back to Home.</p>
          <div className="actions">
            <button className="btn small primary-inline" onClick={() => window.location.reload()}>
              Reload
            </button>
            <a className="btn small" href="/">
              Go to Home
            </a>
          </div>
        </section>
      </div>
    );
  }
}