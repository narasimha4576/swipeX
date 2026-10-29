// Bridge: lets the SwipeX website talk to this extension.
const FROM_WEB = "swipex-web";
const FROM_EXTENSION = "swipex-extension";
const VERSION = chrome.runtime.getManifest().version;

function reply(type, extra) {
  window.postMessage(
    Object.assign({ source: FROM_EXTENSION, type: type }, extra || {}),
    window.location.origin
  );
}

window.addEventListener("message", async (event) => {
  if (event.source !== window || event.origin !== window.location.origin) return;
  const data = event.data;
  if (!data || data.source !== FROM_WEB) return;

  if (data.type === "PING") {
    reply("READY", { version: VERSION });
    return;
  }

  if (data.type === "AUTOFILL") {
    try {
      const result = await chrome.runtime.sendMessage({
        type: "AUTOFILL_START",
        payload: data.payload,
      });
      reply("AUTOFILL_ACK", { ok: Boolean(result && result.ok), error: result && result.error });
    } catch (error) {
      reply("AUTOFILL_ACK", { ok: false, error: String(error) });
    }
  }
});

reply("READY", { version: VERSION });