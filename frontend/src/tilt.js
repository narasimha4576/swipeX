// Cards tilt slightly toward the mouse (laptops only, never on touch screens).
const hasMouse = window.matchMedia("(hover: hover) and (pointer: fine)");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

let current = null;

function reset(card) {
  card.style.setProperty("--rx", "0deg");
  card.style.setProperty("--ry", "0deg");
}

document.addEventListener("pointermove", (event) => {
  if (!hasMouse.matches || reduceMotion.matches) return;
  const card = event.target instanceof Element ? event.target.closest(".job-card") : null;

  if (current && current !== card) {
    reset(current);
    current = null;
  }
  if (!card) return;

  const rect = card.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width - 0.5;
  const y = (event.clientY - rect.top) / rect.height - 0.5;
  card.style.setProperty("--rx", `${(-y * 7).toFixed(2)}deg`);
  card.style.setProperty("--ry", `${(x * 7).toFixed(2)}deg`);
  current = card;
});

document.documentElement.addEventListener("mouseleave", () => {
  if (current) {
    reset(current);
    current = null;
  }
});