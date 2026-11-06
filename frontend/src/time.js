// The server sends times in UTC without a "Z" at the end.
// This makes the browser read them as UTC, so they show correctly in your own time zone.
export function fromServer(value) {
  if (!value) return new Date(NaN);
  const text = String(value);
  return new Date(/(Z|[+-]\d\d:?\d\d)$/.test(text) ? text : text + "Z");
}