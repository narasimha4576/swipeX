// Talks to the SwipeX Autofill browser extension (built on Day 20).
// The extension listens on this same page and answers these messages.
const FROM_WEB = "swipex-web";
const FROM_EXTENSION = "swipex-extension";

function waitFor(type, timeout) {
  return new Promise((resolve) => {
    function onMessage(event) {
      if (event.source !== window) return;
      const data = event.data;
      if (data && data.source === FROM_EXTENSION && data.type === type) finish(data);
    }
    function finish(value) {
      window.removeEventListener("message", onMessage);
      clearTimeout(timer);
      resolve(value);
    }
    window.addEventListener("message", onMessage);
    const timer = setTimeout(() => finish(null), timeout);
  });
}

export async function detectExtension() {
  const reply = waitFor("READY", 700);
  window.postMessage({ source: FROM_WEB, type: "PING" }, window.location.origin);
  return (await reply) !== null;
}

export async function sendAutofill(payload) {
  const reply = waitFor("AUTOFILL_ACK", 4000);
  window.postMessage({ source: FROM_WEB, type: "AUTOFILL", payload }, window.location.origin);
  const ack = await reply;
  return Boolean(ack && ack.ok);
}