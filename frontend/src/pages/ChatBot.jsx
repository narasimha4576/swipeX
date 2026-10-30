import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import api, { errorMessage } from "../api";

const GREETING =
  "Hi! I am SwipeX Help. Ask me how to use SwipeX, how autofill works, or how to spot a fake job.";
const SUGGESTIONS = [
  "How do I apply with autofill?",
  "How can I tell a job is fake?",
  "What does Verified only do?",
];

export default function ChatBot() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: "assistant", content: GREETING }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef(null);

  useEffect(() => {
    if (open && bottom.current) bottom.current.scrollIntoView({ block: "end" });
  }, [messages, open, busy]);

  async function send(text) {
    const content = text.trim();
    if (!content || busy) return;
    const next = [...messages, { role: "user", content }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const history = next.slice(1).slice(-10);
      const { data } = await api.post("/chat", { messages: history, page: location.pathname });
      setMessages([...next, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setMessages([...next, { role: "assistant", content: errorMessage(err) }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {open && (
        <div className="chat-panel">
          <div className="chat-head">
            <span>SwipeX Help</span>
            <button className="btn small" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
          <div className="chat-body">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "chat-msg user" : "chat-msg"}>
                {m.content}
              </div>
            ))}
            {messages.length === 1 && (
              <div className="chat-suggest">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="fchip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
            {busy && <div className="chat-msg muted">Thinking...</div>}
            <div ref={bottom} />
          </div>
          <form
            className="chat-form"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              placeholder="Ask a question..."
              maxLength={1000}
            />
            <button className="btn small primary-inline" disabled={busy || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
      <button className="chat-fab" onClick={() => setOpen(!open)} aria-label="Open help chat">
        Help
      </button>
    </>
  );
}