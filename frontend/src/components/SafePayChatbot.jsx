import { useEffect, useRef, useState } from 'react';
import './SafePayChatbot.css';

const DEFAULT_API = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'}/chat`;
const starterQuestions = [
  'What does a high risk score mean?',
  'How does anomaly detection work?',
  'How should I investigate a suspicious transaction?'
];

export default function SafePayChatbot({
  apiUrl = DEFAULT_API,
  transactionContext = null,
  comparisonTransactions = [],
  title = 'SafePay Assistant'
}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [activeTransactionId, setActiveTransactionId] = useState('');
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hello! I'm your SafePay Assistant. Ask me about fraud risk, transaction analysis, account networks, alerts, or investigations." }
  ]);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  async function sendMessage(text) {
    const question = (text ?? input).trim();
    if (!question || busy) return;
    const mentionedIds = question.match(/\b(?:TXN|TX)[-_]?[A-Za-z0-9][A-Za-z0-9_-]*\b/gi) || [];
    const transactionId = mentionedIds[0] || activeTransactionId;
    if (mentionedIds[0]) setActiveTransactionId(mentionedIds[0]);
    const requestMessage = transactionId && !mentionedIds.length ? `${question} (transaction ${transactionId})` : question;
    const nextMessages = [...messages, { role: 'user', content: question }];
    setMessages(nextMessages);
    setInput('');
    setBusy(true);
    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(sessionStorage.getItem('safepay_access_token') ? { Authorization: `Bearer ${sessionStorage.getItem('safepay_access_token')}` } : {})
        },
        body: JSON.stringify({
          message: requestMessage,
          history: messages.slice(-10),
          transaction_context: transactionContext,
          comparison_context: comparisonTransactions
        })
      });
      if (!response.ok) {
        let detail = '';
        try {
          const errorData = await response.json();
          detail = typeof errorData.detail === 'string' ? `: ${errorData.detail}` : '';
        } catch {
          detail = '';
        }
        throw new Error(`Chat service returned HTTP ${response.status}${detail}`);
      }
      const data = await response.json();
      setMessages(current => [...current, { role: 'assistant', content: data.reply || 'I could not prepare a response.' }]);
    } catch (error) {
      setMessages(current => [...current, {
        role: 'assistant',
        content: error instanceof TypeError
          ? `I cannot reach the SafePay chat service at ${apiUrl}. Start the FastAPI backend and check that its CORS settings allow this frontend.`
          : `The SafePay chat service returned an error: ${error.message}`
      }]);
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage();
  }

  return (
    <div className="sp-chat-root">
      {open && (
        <section className="sp-chat-panel" aria-label="SafePay chatbot">
          <header className="sp-chat-header">
            <div className="sp-chat-brand">
              <div className="sp-chat-mark">S</div>
              <div><strong>{title}</strong><span>Financial investigation support</span></div>
            </div>
            <button className="sp-chat-close" onClick={() => setOpen(false)} aria-label="Close chatbot">×</button>
          </header>
          <div className="sp-chat-notice">Here to help with your review. Please verify important findings.</div>
          <div className="sp-chat-messages">
            {messages.map((message, index) => (
              <div className={`sp-chat-row ${message.role}`} key={`${message.role}-${index}`}>
                <div className="sp-chat-bubble">{message.content}</div>
              </div>
            ))}
            {busy && <div className="sp-chat-row assistant"><div className="sp-chat-bubble sp-chat-typing">SafePay is thinking…</div></div>}
            <div ref={endRef} />
          </div>
          {messages.length === 1 && (
            <div className="sp-chat-starters">
              {starterQuestions.map(question => <button key={question} onClick={() => sendMessage(question)}>{question}</button>)}
            </div>
          )}
          <form className="sp-chat-form" onSubmit={handleSubmit}>
            <input value={input} onChange={event => setInput(event.target.value)} placeholder="Ask SafePay Assistant…" maxLength={4000} aria-label="Message" />
            <button type="submit" disabled={!input.trim() || busy} aria-label="Send message">➤</button>
          </form>
          <div className="sp-chat-footer">Never share passwords, PINs, or OTPs.</div>
        </section>
      )}
      <button className="sp-chat-launcher" onClick={() => setOpen(value => !value)} aria-label={open ? 'Close SafePay Assistant' : 'Open SafePay Assistant'}>
        <span className="sp-chat-launcher-icon">{open ? '×' : '✦'}</span>
        <span>{open ? 'Close' : 'Ask SafePay'}</span>
      </button>
    </div>
  );
}
