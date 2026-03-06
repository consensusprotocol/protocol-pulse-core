import React, { useEffect, useRef, useState, useCallback } from "react";
import { OracleAvatar } from "./oracle-avatar";

const API_BASE = (typeof import.meta !== "undefined" && import.meta.env?.VITE_ORACLE_API) 
  || window.ORACLE_API_BASE 
  || "http://localhost:8200";

const STATUS_COLORS = {
  idle: "#b8c2d9", listening: "#66d9ff",
  thinking: "#f4c46f", speaking: "#6cff9f", interrupted: "#ff8a8a",
};

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
  const [error, setError] = useState(null);

  useEffect(() => {
    const avatar = new OracleAvatar(canvasRef.current, {
      width: 512, height: 512, useSprites: false,
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
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: conversationIdRef.current, interrupt_id }),
      });
    } catch (_) {}
    if (pendingControllerRef.current) {
      pendingControllerRef.current.abort();
      pendingControllerRef.current = null;
    }
    avatarRef.current?.interrupt();
    setStatus("interrupted");
    setTimeout(() => setStatus("idle"), 220);
  }, []);

  const askOracle = useCallback(async () => {
    if (!question.trim() || !avatarRef.current) return;
    if (["speaking","thinking","listening"].includes(status)) {
      await sendInterrupt();
    }
    const interrupt_id = crypto.randomUUID();
    interruptIdRef.current = interrupt_id;
    const controller = new AbortController();
    pendingControllerRef.current = controller;
    setError(null);
    const t0 = performance.now();
    try {
      avatarRef.current.startThinking();
      setStatus("thinking");
      setTranscript("");
      const res = await fetch(`${API_BASE}/oracle/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      if (err?.name !== "AbortError") {
        console.error("Oracle ask failed:", err);
        setError(err.message);
      }
      setStatus("idle");
    } finally {
      pendingControllerRef.current = null;
    }
  }, [question, status, sendInterrupt]);

  const handleKey = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) askOracle();
  };

  return (
    <div style={styles.shell}>
      <div style={styles.avatarPanel}>
        <canvas ref={canvasRef} style={styles.canvas} />
        <div style={{ ...styles.badge, color: STATUS_COLORS[status] || "#fff" }}>
          ● {status.toUpperCase()}
        </div>
        {latency && (
          <div style={styles.latencyBadge}>{latency}ms</div>
        )}
      </div>

      <div style={styles.controls}>
        <div style={styles.title}>PROTOCOL PULSE ORACLE</div>
        <div style={styles.subtitle}>
          Live avatar · viseme runtime · Bitcoin-native · interrupt-aware
        </div>

        <textarea
          style={styles.input}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask Oracle about Bitcoin, mining, hashrate, macro, wallets... (⌘+Enter to submit)"
          rows={5}
        />

        <div style={styles.buttons}>
          <button style={styles.btnPrimary} onClick={askOracle}>
            Ask Oracle
          </button>
          <button style={styles.btnSecondary} onClick={sendInterrupt}>
            Interrupt
          </button>
        </div>

        {error && (
          <div style={styles.errorBox}>{error}</div>
        )}

        <div style={styles.transcriptBox}>
          <div style={styles.transcriptLabel}>ORACLE SAYS</div>
          <div style={styles.transcriptBody}>{transcript || "Awaiting your question..."}</div>
        </div>

        <div style={styles.stateGuide}>
          {Object.entries(STATUS_COLORS).map(([s, c]) => (
            <span key={s} style={{ color: c, marginRight: 16, fontSize: 11 }}>● {s}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  shell: { display:"grid", gridTemplateColumns:"540px 1fr", gap:24, alignItems:"start", width:"100%", maxWidth:1100, margin:"0 auto", padding:24, color:"#eef3ff", fontFamily:"Inter,ui-sans-serif,sans-serif", background:"#050810" },
  avatarPanel: { position:"relative", background:"rgba(8,12,19,0.85)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:24, padding:14, boxShadow:"0 18px 60px rgba(0,0,0,0.4)" },
  canvas: { width:512, height:512, display:"block", borderRadius:18, background:"#090d12" },
  badge: { position:"absolute", top:22, left:22, fontSize:11, letterSpacing:"0.12em", fontWeight:700, padding:"7px 10px", borderRadius:999, border:"1px solid rgba(255,255,255,0.07)", background:"rgba(0,0,0,0.38)" },
  latencyBadge: { position:"absolute", top:22, right:22, fontSize:11, color:"#f4c46f", fontWeight:700, padding:"7px 10px", borderRadius:999, border:"1px solid rgba(255,255,255,0.07)", background:"rgba(0,0,0,0.38)" },
  controls: { background:"rgba(8,12,19,0.85)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:24, padding:22, boxShadow:"0 18px 60px rgba(0,0,0,0.4)" },
  title: { fontSize:26, fontWeight:800, letterSpacing:"-0.03em", color:"#eef3ff" },
  subtitle: { color:"#7a8fad", marginTop:6, marginBottom:18, fontSize:13 },
  input: { width:"100%", minHeight:120, background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.08)", color:"#eef3ff", borderRadius:14, padding:"12px 14px", resize:"vertical", fontFamily:"inherit", fontSize:14, boxSizing:"border-box" },
  buttons: { display:"flex", gap:12, marginTop:14 },
  btnPrimary: { appearance:"none", border:"none", borderRadius:12, padding:"11px 20px", fontWeight:700, cursor:"pointer", background:"linear-gradient(90deg,#cc0000,#f0943a)", color:"#fff", fontSize:14 },
  btnSecondary: { appearance:"none", borderRadius:12, padding:"11px 20px", fontWeight:700, cursor:"pointer", background:"rgba(255,255,255,0.06)", color:"#eef3ff", border:"1px solid rgba(255,255,255,0.1)", fontSize:14 },
  errorBox: { marginTop:12, padding:"10px 14px", borderRadius:10, background:"rgba(204,0,0,0.15)", border:"1px solid rgba(204,0,0,0.3)", color:"#ff8a8a", fontSize:13 },
  transcriptBox: { background:"rgba(255,255,255,0.02)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:14, padding:"14px 16px", marginTop:18 },
  transcriptLabel: { fontSize:10, letterSpacing:"0.18em", color:"#f4c46f", fontWeight:800, marginBottom:10 },
  transcriptBody: { color:"#dce5f7", lineHeight:1.6, minHeight:80, fontSize:14 },
  stateGuide: { marginTop:16, paddingTop:12, borderTop:"1px solid rgba(255,255,255,0.06)" },
};
