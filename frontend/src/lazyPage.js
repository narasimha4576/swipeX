import { createElement, lazy, Suspense } from "react";

// A page that is downloaded only when someone opens it. The header stays visible while it loads.
export function lazyPage(loader) {
  const Page = lazy(loader);
  function LazyPage(props) {
    const waiting = createElement("p", { className: "muted", style: { padding: "2rem" } }, "Loading...");
    return createElement(Suspense, { fallback: waiting }, createElement(Page, props));
  }
  return LazyPage;
}