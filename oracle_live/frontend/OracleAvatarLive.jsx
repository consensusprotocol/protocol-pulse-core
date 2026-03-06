import React, { useEffect, useRef, useState, useCallback } from "react";
import { OracleAvatar } from "./oracle-avatar";
import "./oracle-avatar.css";

const API_BASE = (typeof import.meta !== "undefined" && import.meta.env?.VITE_ORACLE_API) || "http://localhost:8201";

export default function OracleAvatarLive() {
  const canvasRef = useRef(null);
  const avatarRef = useRef(null);
  const interruptIdRef = useRef(null);
  const conversationIdRef = useRef(crypto.randomUUID());
  const pendingControllerRef = useRef(null);

  const [question, setQuestion] = useState("");
  const [transcript, setTranscript] = useState("");
  const [status, setStatus] = useState("idle");
  const [latency, setLatency] = useState(null);

  useEffect(() => {
    const avatar = new OracleAvatar(canvasRef.current, {
      width: 512, height: 512,
      useSprites: false,
      assetsBase: "/static/avatar/visemes",
    });
    avatarRef.current = avatar;
    return () => avatar.destroy();
  }, []);

  const sendInterrupt = useCallback(async () => {
    const interrupt_id = crypto.randomUUID();
    interruptIdRef.current = interrupt_id;
    try {
      await fetch(`${API_BASE}/oracle/interrupt`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: conversationIdRef.current, interrupt_id }),
      });
    } catch (_) {}
    if (pendingControllerRef.current) {
      pendingControllerRef.current.abort(); pendingControllerRef.current = null;
    }
    avatarRef.current?.interrupt();
    setStatus("interrupted");
    setTimeout(() => setStatus("idle"), 180);
  }, []);

  const askOracle = useCallback(async () => {
    if (!question.trim() || !avatarRef.current) return;
    if (["speaking","thinking","listening"].includes(status)) await sendInterrupt();

    const interrupt_id = crypto.randomUUID();
    interruptIdRef.current = interrupt_id;
    const controller = new AbortController();
    pendingControllerRef.current = controller;
    const t0 = performance.now();

    try {
      avatarRef.current.startThinking();
      setStatus("thinking"); setTranscript("");

      const res = await fetch(`${API_BASE}/oracle/ask`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          question: question.trim(),
          conversation_id: conversationIdRef.current,
          interrupt_id,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const payload = await res.json();
      if (interruptIdRef.current !== payload.interrupt_id) return;

      setLatency(Math.round(performance.now() - t0));
      setTranscript(payload.answer_text);
      setStatus("speaking");
      await avatarRef.current.speak(payload.audio_base64, payload.viseme_timeline);
      setStatus("idle");
    } catch (err) {
      if (err?.name !== "AbortError") console.error("Oracle ask failed:", err);
      setStatus("idle");
    } finally {
      pendingControllerRef.current = null;
    }
  }, [question, status, sendInterrupt]);

  const handleKey = useCallback((e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); askOracle(); }
  }, [askOracle]);

  return (
    <div className="oracle-shell">
      <div className="avatar-panel">
        <canvas ref={canvasRef} className="oracle-canvas" />
        <div className={`oracle-status status-${status}`}>{status.toUpperCase()}</div>
        {latency && <div className="oracle-latency">{latency}ms</div>}
      </div>
      <div className="oracle-controls">
        <div className="oracle-title">PROTOCOL PULSE ORACLE</div>
        <div className="oracle-subtitle">Live avatar — V1 architecture</div>
        <textarea className="oracle-input" value={question}
          onChange={e => setQuestion(e.target.value)} onKeyDown={handleKey}
          placeholder="Ask about Bitcoin, mining, macro, on-chain data, hardware..." />
        <div className="oracle-buttons">
          <button className="btn btn-primary" onClick={askOracle}
            disabled={["thinking","speaking"].includes(status)}>
            {status === "thinking" ? "Thinking..." : status === "speaking" ? "Speaking..." : "Ask Oracle"}
          </button>
          <button className="btn btn-secondary" onClick={sendInterrupt}>Interrupt</button>
        </div>
        <div className="oracle-transcript">
          <div className="transcript-label">LATEST RESPONSE</div>
          <div className="transcript-body">{transcript || "…"}</div>
        </div>
        <div className="oracle-note">
          V1: latency win + state machine + Bitcoin lexicon. V2: streaming TTS + Proto-P asset shell.
        </div>
      </div>
    </div>
  );
}
