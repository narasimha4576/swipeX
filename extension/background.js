// Background worker: opens the company page and keeps your details for that one tab.
const TTL_MS = 15 * 60 * 1000;
const MAX_BYTES = 9 * 1000 * 1000;
const TEST_PAGE = /^http:\/\/(localhost|127\.0\.0\.1):5173\//;
const storageKey = (tabId) => "tab_" + tabId;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handle(message, sender)
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: String(error) }));
  return true;
});

async function handle(message, sender) {
  if (message && message.type === "AUTOFILL_START") return startAutofill(message.payload);
  if (message && message.type === "GET_PAYLOAD") return getPayload(sender);
  return { ok: false, error: "Unknown request" };
}

async function startAutofill(payload) {
  const url = payload && payload.job && payload.job.apply_url;
  const safe = typeof url === "string" && (/^https:\/\//i.test(url) || TEST_PAGE.test(url));
  if (!safe) return { ok: false, error: "The apply link is not a safe web address" };
  if (!payload.applicant) return { ok: false, error: "No applicant details were sent" };
  if (JSON.stringify(payload).length > MAX_BYTES) {
    return { ok: false, error: "The resume file is too large for autofill" };
  }

  const tab = await chrome.tabs.create({ url, active: true });
  await chrome.storage.session.set({
    [storageKey(tab.id)]: { payload, expires: Date.now() + TTL_MS },
  });
  return { ok: true };
}

async function getPayload(sender) {
  const tabId = sender.tab && sender.tab.id;
  if (tabId === undefined) return { ok: false };
  const stored = await chrome.storage.session.get(storageKey(tabId));
  const entry = stored[storageKey(tabId)];
  if (!entry) return { ok: false };
  if (Date.now() > entry.expires) {
    await chrome.storage.session.remove(storageKey(tabId));
    return { ok: false };
  }
  return { ok: true, payload: entry.payload };
}

chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.session.remove(storageKey(tabId));
});