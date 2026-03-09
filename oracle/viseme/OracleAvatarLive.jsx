/**
 * OracleAvatarLive — React component for Protocol Pulse live avatar.
 * Integrates OracleAvatar canvas engine with text input and Web Speech barge-in.
 */
import React, { useRef, useEffect, useState, useCallback } from 'react';

const AVATAR_SIZE = 512;

export default function OracleAvatarLive({ apiBase = '', assetsPath = '/oracle/viseme/assets/frames/' }) {
  const canvasRef = useRef(null);
  const avatarRef = useRef(null);
  const recognitionRef = useRef(null);
  const [input, setInput] = useState('');
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('idle');

  // Initialize avatar engine
  useEffect(() => {
    const script = document.createElement('script');
    script.src = `${apiBase}/oracle/viseme/oracle-avatar.js`;
    script.onload = () => {
      if (canvasRef.current && window.OracleAvatar) {
        const avatar = new window.OracleAvatar(canvasRef.current, {
          basePath: assetsPath,
          apiUrl: apiBase,
        });
        avatar.loadAssets(assetsPath).then(() => avatar.start()).catch(() => avatar.start());
        avatarRef.current = avatar;
      }
    };
    document.head.appendChild(script);

    return () => {
      if (avatarRef.current) avatarRef.current.destroy();
      document.head.removeChild(script);
    };
  }, [apiBase, assetsPath]);

  // Web Speech API barge-in detection
  useEffect(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = () => {
      // User spoke while avatar is speaking — interrupt
      if (avatarRef.current && avatarRef.current.isPlaying) {
        avatarRef.current.interrupt();
        setStatus('interrupted');
      }
    };

    recognition.onerror = () => {};
    recognitionRef.current = recognition;

    try { recognition.start(); } catch (e) {}

    return () => {
      try { recognition.stop(); } catch (e) {}
    };
  }, []);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setLoading(true);
    setStatus('thinking');
    setTranscript('');

    // Immediately trigger thinking state
    if (avatarRef.current) avatarRef.current.thinking();

    try {
      const resp = await fetch(`${apiBase}/generate/viseme`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });

      if (!resp.ok) throw new Error(`Server error ${resp.status}`);

      const data = await resp.json();

      if (data.error) throw new Error(data.error);

      setTranscript(text);
      setStatus('speaking');

      if (avatarRef.current) {
        await avatarRef.current.speak(data.audio_base64, data.viseme_timeline);
      }
    } catch (err) {
      setStatus('error');
      setTranscript(`Error: ${err.message}`);
    } finally {
      setLoading(false);
      setInput('');
    }
  }, [input, loading, apiBase]);

  return (
    <div style={styles.container}>
      <div style={styles.avatarWrapper}>
        <canvas
          ref={canvasRef}
          width={AVATAR_SIZE}
          height={AVATAR_SIZE}
          style={styles.canvas}
        />
        <div style={styles.statusBadge}>
          <span style={{
            ...styles.statusDot,
            backgroundColor: status === 'speaking' ? '#cc0000' :
                            status === 'thinking' ? '#F7931A' :
                            status === 'error' ? '#ff4444' : '#333'
          }} />
          {status.toUpperCase()}
        </div>
      </div>

      {transcript && (
        <div style={styles.transcript}>
          <span style={styles.transcriptLabel}>ORACLE:</span> {transcript}
        </div>
      )}

      <form onSubmit={handleSubmit} style={styles.form}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the Oracle..."
          style={styles.input}
          disabled={loading}
        />
        <button type="submit" style={styles.button} disabled={loading}>
          {loading ? '...' : 'ASK'}
        </button>
      </form>

      <div style={styles.branding}>
        PROTOCOL PULSE <span style={{ color: '#cc0000' }}>ORACLE</span>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
    padding: '24px',
    backgroundColor: '#000',
    borderRadius: '12px',
    border: '1px solid #1a1a1a',
    maxWidth: '560px',
    margin: '0 auto',
    fontFamily: "'JetBrains Mono', monospace",
  },
  avatarWrapper: {
    position: 'relative',
    width: AVATAR_SIZE,
    height: AVATAR_SIZE,
  },
  canvas: {
    borderRadius: '8px',
    border: '1px solid #1a1a1a',
    width: '100%',
    height: '100%',
  },
  statusBadge: {
    position: 'absolute',
    top: '8px',
    right: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 8px',
    backgroundColor: 'rgba(0,0,0,0.8)',
    borderRadius: '4px',
    fontSize: '10px',
    color: '#666',
    letterSpacing: '1px',
  },
  statusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    display: 'inline-block',
  },
  transcript: {
    width: '100%',
    padding: '12px',
    backgroundColor: '#0a0a0a',
    borderRadius: '6px',
    border: '1px solid #1a1a1a',
    fontSize: '13px',
    color: '#aaa',
    lineHeight: '1.5',
    maxHeight: '120px',
    overflowY: 'auto',
  },
  transcriptLabel: {
    color: '#cc0000',
    fontWeight: 'bold',
    fontSize: '11px',
  },
  form: {
    display: 'flex',
    width: '100%',
    gap: '8px',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    backgroundColor: '#0a0a0a',
    border: '1px solid #333',
    borderRadius: '6px',
    color: '#eee',
    fontSize: '14px',
    fontFamily: "'JetBrains Mono', monospace",
    outline: 'none',
  },
  button: {
    padding: '10px 20px',
    backgroundColor: '#cc0000',
    border: 'none',
    borderRadius: '6px',
    color: '#fff',
    fontSize: '13px',
    fontWeight: 'bold',
    fontFamily: "'JetBrains Mono', monospace",
    cursor: 'pointer',
    letterSpacing: '1px',
  },
  branding: {
    fontSize: '10px',
    color: '#333',
    letterSpacing: '2px',
    textTransform: 'uppercase',
  },
};
