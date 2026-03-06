
import React, { useEffect, useRef, useState, useCallback } from "react";
import { OracleAvatar }         from "./oracle-avatar";
import { VoiceOrbRenderer }     from "./VoiceOrbRenderer";
import { HologramActivation }   from "./HologramActivation";
import "./oracle-avatar.css";

const API_BASE = (typeof import !== "undefined" && import.meta?.env?.VITE_ORACLE_API)
  || "http://localhost:8202";

export default function OracleStage() {
  const canvasRef        = useRef(null);
  const avatarRef        = useRef(null);   // OracleAvatar instance
  const orbRef           = useRef(null);   // VoiceOrbRenderer instance
  const activationRef    = useRef(null);   // HologramActivation instance
  const audioCtxRef      = useRef(null);
  const analyserRef      = useRef(null);
  const interruptIdRef   = useRef(null);
  const convIdRef        = useRef(crypto.randomUUID());
  const pendingCtrlRef   = useRef(null);
  const micRef           = useRef(null);

  const [mode,      setMode]      = useState("voice");  // "voice" | "activating" | "avatar"
  const [status,    setStatus]    = useState("idle");
  const [question,  setQuestion]  = useState("");
  const [transcript,setTranscript]= useState("");
  const [latency,   setLatency]   = useState(null);
  const [visionOn,  setVisionOn]  = useState(false);

  // ── Init audio context shared by both modes ───────────────────────────────
  const initAudio = useCallback(() => {
    if (audioCtxRef.current) return;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    audioCtxRef.current = new Ctx();
    analyserRef.current = audioCtxRef.current.createAnalyser();
    analyserRef.current.fftSize = 256;
  }, []);

  // ── Mount: start in Voice Orb mode ───────────────────────────────────────
  useEffect(() => {
    initAudio();
    const orb = new VoiceOrbRenderer(canvasRef.current, { width: 512, height: 512 });
    orb.connectAudio(audioCtxRef.current, analyserRef.current);
    orbRef.current = orb;
    return () => {
      orb.destroy();
      avatarRef.current?.destroy();
    };
  }, []);

  // ── Sync state label to active renderer ───────────────────────────────────
  useEffect(() => {
    if (mode === "voice" && orbRef.current) {
      orbRef.current.setState(status);
      orbRef.current.setVisionActive(visionOn);
    }
    if (mode === "avatar" && avatarRef.current) {
      avatarRef.current.setState(status);
    }
  }, [status, mode, visionOn]);

  // ── Interrupt ─────────────────────────────────────────────────────────────
  const sendInterrupt = useCallback(async () => {
    const iid = crypto.randomUUID();
    interruptIdRef.current = iid;
    try {
      await fetch(`${API_BASE}/oracle/interrupt`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: convIdRef.current, interrupt_id: iid }),
      });
    } catch (_) {}
    pendingCtrlRef.current?.abort();
    pendingCtrlRef.current = null;
    if (mode === "voice")  { orbRef.current?.triggerInterrupt(); }
    if (mode === "avatar") { avatarRef.current?.interrupt(); }
    setStatus("interrupted");
    setTimeout(() => setStatus("idle"), 220);
  }, [mode]);

  // ── Ask Oracle ────────────────────────────────────────────────────────────
  const askOracle = useCallback(async () => {
    if (!question.trim()) return;
    if (["speaking","thinking","listening"].includes(status)) await sendInterrupt();

    const iid = crypto.randomUUID();
    interruptIdRef.current = iid;
    const ctrl = new AbortController();
    pendingCtrlRef.current = ctrl;
    const t0 = performance.now();

    try {
      if (audioCtxRef.current?.state === "suspended") await audioCtxRef.current.resume();
      setStatus("thinking"); setTranscript("");

      const res = await fetch(`${API_BASE}/oracle/ask`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        signal: ctrl.signal,
        body: JSON.stringify({
          question: question.trim(),
          conversation_id: convIdRef.current,
          interrupt_id: iid,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const payload = await res.json();
      if (interruptIdRef.current !== payload.interrupt_id) return;

      setLatency(Math.round(performance.now() - t0));
      setTranscript(payload.answer_text);
      setStatus("speaking");

      // Decode audio + wire to analyser
      const bytes  = Uint8Array.from(atob(payload.audio_base64), c => c.charCodeAt(0));
      const buffer = await audioCtxRef.current.decodeAudioData(bytes.buffer.slice(0));
      const source = audioCtxRef.current.createBufferSource();
      source.buffer = buffer;
      source.connect(analyserRef.current);
      analyserRef.current.connect(audioCtxRef.current.destination);

      if (mode === "avatar") {
        // Let avatar handle playback + viseme sync
        await avatarRef.current.speak(payload.audio_base64, payload.viseme_timeline);
      } else {
        // Voice mode: just play audio, orb reacts to analyser
        source.start(0);
        await new Promise(resolve => { source.onended = resolve; });
      }
      setStatus("idle");
    } catch (err) {
      if (err?.name !== "AbortError") console.error(err);
      setStatus("idle");
    } finally { pendingCtrlRef.current = null; }
  }, [question, status, sendInterrupt, mode]);

  // ── Hologram activation ───────────────────────────────────────────────────
  const activateAvatar = useCallback(async () => {
    if (mode === "avatar") {
      // Deactivate: destroy avatar, restart orb
      avatarRef.current?.destroy();
      avatarRef.current = null;
      const orb = new VoiceOrbRenderer(canvasRef.current, { width: 512, height: 512 });
      orb.connectAudio(audioCtxRef.current, analyserRef.current);
      orb.setState(status);
      orbRef.current = orb;
      setMode("voice");
      return;
    }

    setMode("activating");
    orbRef.current?.destroy();
    orbRef.current = null;

    // Create avatar in background (procedural, no assets needed)
    const avatar = new OracleAvatar(canvasRef.current, { width: 512, height: 512, useSprites: false });
    avatarRef.current = avatar;
    avatar.setState("idle");

    // Run activation sequence — avatarRenderFn draws the resolved avatar
    const activation = new HologramActivation(canvasRef.current);
    activationRef.current = activation;

    await activation.run(
      (ctx, progress) => {
        // During activation, avatar renders with opacity
        ctx.save();
        ctx.globalAlpha = Math.min(1, progress * 1.4);
        avatar._render(); // renders to its own canvas
        // For the activation we composite from the avatar's canvas
        ctx.drawImage(canvasRef.current, 0, 0);
        ctx.restore();
      },
      () => {
        // Avatar blinks once on system-online
        avatar.setState("idle");
        setMode("avatar");
        setStatus("idle");
      }
    );
  }, [mode, status]);

  const handleKey = useCallback((e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); askOracle(); }
  }, [askOracle]);

  const busy = ["thinking","speaking"].includes(status);

  return (
    <div className="oracle-shell">
      <div className="avatar-panel">
        <canvas ref={canvasRef} className="oracle-canvas" />

        <div className={`oracle-status status-${status}`}>{status.toUpperCase()}</div>
        {latency && <div className="oracle-latency">{latency}ms</div>}

        {/* Mode toggle */}
        <button
          className={`oracle-mode-btn ${mode === "avatar" ? "active" : ""}`}
          onClick={activateAvatar}
          title={mode === "avatar" ? "Minimize Oracle" : "Activate Visual Oracle"}
        >
          {mode === "activating" ? "▶▶" : mode === "avatar" ? "▼ Minimize" : "◈ Activate Oracle"}
        </button>

        {/* Vision toggle */}
        <button
          className={`oracle-vision-btn ${visionOn ? "active" : ""}`}
          onClick={() => setVisionOn(v => !v)}
          title="Toggle Gemini Vision"
        >
          {visionOn ? "◉ Vision" : "○ Vision"}
        </button>
      </div>

      <div className="oracle-controls">
        <div className="oracle-title">PROTOCOL PULSE ORACLE</div>
        <div className="oracle-subtitle">
          {mode === "voice" ? "Voice presence — HER mode" :
           mode === "avatar" ? "Visual Oracle — Proto-P active" : "Activating…"}
        </div>

        <textarea
          className="oracle-input"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about Bitcoin, mining, macro, on-chain data, hardware..."
        />

        <div className="oracle-buttons">
          <button className="btn btn-primary" onClick={askOracle} disabled={busy}>
            {status === "thinking" ? "Thinking…" : status === "speaking" ? "Speaking…" : "Ask Oracle"}
          </button>
          <button className="btn btn-secondary" onClick={sendInterrupt}>Interrupt</button>
        </div>

        <div className="oracle-transcript">
          <div className="transcript-label">LATEST RESPONSE</div>
          <div className="transcript-body">{transcript || "…"}</div>
        </div>

        {latency && (
          <div className="oracle-perf">
            Response: {latency}ms · Mode: {mode} · State: {status}
          </div>
        )}

        <div className="oracle-note">
          Voice mode: HER-style signal presence · Avatar mode: Proto-P visual oracle<br/>
          V2: mouth atlas + streaming TTS · V3: 2.5D parallax + mic turn-taking
        </div>
      </div>
    </div>
  );
}
