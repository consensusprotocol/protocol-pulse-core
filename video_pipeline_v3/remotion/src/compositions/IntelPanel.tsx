import React from 'react';
import { useCurrentFrame, useVideoConfig, AbsoluteFill, interpolate, spring, Easing } from 'remotion';
import { BRAND } from '../brand';

interface IntelPanelProps {
  btcPrice: string;
  narrative: string;
  marketMood: string;
  quoteText: string;
  quoteHandle: string;
  durationInFrames: number;
}

export const IntelPanel: React.FC<IntelPanelProps> = ({
  btcPrice, narrative, marketMood, quoteText, quoteHandle, durationInFrames
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // Panel slides in from left (spring, frames 0-20)
  const panelX = spring({ frame, fps, config: { damping: 18, stiffness: 120 } });
  const panelSlide = interpolate(panelX, [0, 1], [-980, 0]);

  // BTC price counter animates up (frames 0-45)
  const priceReveal = interpolate(frame, [0, 45], [0, 1], { extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });

  // Narrative types in (frames 30-70)
  const narrativeChars = Math.floor(interpolate(frame, [30, 70], [0, narrative.length], { extrapolateRight: 'clamp' }));

  // Quote fades in (frames 55-80)
  const quoteOpacity = interpolate(frame, [55, 80], [0, 1], { extrapolateRight: 'clamp' });

  // Pulsing red glow on mood pill (continuous)
  const glowPulse = 0.4 + 0.3 * Math.sin(t * Math.PI * 1.2);

  // Scanning line (top to bottom of panel, every 4s)
  const scanY = ((t % 4) / 4) * 430;

  // Corner bracket blink (every 3s)
  const bracketOpacity = 0.3 + 0.4 * Math.abs(Math.sin(t * Math.PI * 0.33));

  return (
    <AbsoluteFill style={{ transform: `translateX(${panelSlide}px)` }}>
      {/* Glass panel base */}
      <div style={{
        position: 'absolute', left: 64, top: 222, width: 960, height: 430,
        background: 'linear-gradient(135deg, rgba(5,6,10,0.92) 0%, rgba(10,8,15,0.88) 100%)',
        borderTop: `2px solid ${BRAND.RED}`,
        borderLeft: `2px solid rgba(255,0,0,0.6)`,
        borderRight: `1px solid rgba(255,255,255,0.05)`,
        borderBottom: `1px solid rgba(255,255,255,0.08)`,
        backdropFilter: 'blur(8px)',
        overflow: 'hidden',
      }}>

        {/* Scanning line */}
        <div style={{
          position: 'absolute', left: 0, top: scanY, width: '100%', height: 1,
          background: 'linear-gradient(90deg, transparent, rgba(255,0,0,0.15), transparent)',
          pointerEvents: 'none',
        }} />

        {/* Inner glass shimmer */}
        <div style={{
          position: 'absolute', left: 2, top: 4, width: '97%', height: 1,
          background: 'rgba(255,255,255,0.07)',
        }} />

        {/* BTC PRICE */}
        <div style={{ position: 'absolute', left: 16, top: 14 }}>
          <div style={{
            fontFamily: 'monospace', fontSize: 11, letterSpacing: 3,
            color: `rgba(248,193,92,0.65)`, marginBottom: 4,
          }}>BTC LIVE</div>

          <div style={{
            fontFamily: 'sans-serif', fontWeight: 900, fontSize: 52,
            color: BRAND.GOLD,
            textShadow: `0 0 30px rgba(248,193,92,${0.3 * priceReveal}), 0 0 60px rgba(248,193,92,${0.15 * priceReveal})`,
            opacity: 0.3 + 0.7 * priceReveal,
            letterSpacing: -1,
          }}>{btcPrice}</div>
        </div>

        {/* Timestamp */}
        <div style={{
          position: 'absolute', right: 16, top: 22,
          fontFamily: 'monospace', fontSize: 10,
          color: 'rgba(255,255,255,0.25)', letterSpacing: 2,
        }}>{new Date().toISOString().slice(11,16)} UTC</div>

        {/* Section divider */}
        <div style={{
          position: 'absolute', left: 16, top: 94, width: 928, height: 1,
          background: 'rgba(255,255,255,0.07)',
        }} />

        {/* NARRATIVE */}
        <div style={{ position: 'absolute', left: 16, top: 104 }}>
          <div style={{
            fontFamily: 'monospace', fontSize: 10, letterSpacing: 3,
            color: `rgba(255,0,0,0.6)`, marginBottom: 6,
          }}>SIGNAL</div>

          {/* Mood pill */}
          <div style={{
            position: 'absolute', right: -912, top: -4,
            padding: '3px 10px',
            border: `1px solid rgba(255,0,0,${glowPulse})`,
            background: `rgba(255,0,0,0.08)`,
            borderRadius: 2,
            fontFamily: 'monospace', fontSize: 9, letterSpacing: 2,
            color: BRAND.RED,
            boxShadow: `0 0 8px rgba(255,0,0,${glowPulse * 0.5})`,
          }}>{marketMood}</div>

          <div style={{
            fontFamily: 'sans-serif', fontWeight: 700, fontSize: 24,
            color: 'rgba(244,245,248,0.95)', marginTop: 4,
            maxWidth: 920,
          }}>{narrative.slice(0, narrativeChars)}{frame < 70 ? '\u258C' : ''}</div>
        </div>

        {/* Section divider */}
        <div style={{
          position: 'absolute', left: 16, top: 158, width: 928, height: 1,
          background: 'rgba(255,255,255,0.06)',
        }} />

        {/* THOUGHT LEADER QUOTE */}
        {quoteText && (
          <div style={{
            position: 'absolute', left: 16, top: 168,
            opacity: quoteOpacity,
          }}>
            <div style={{
              fontFamily: 'sans-serif', fontSize: 32, fontWeight: 900,
              color: `rgba(255,0,0,0.45)`, lineHeight: 1, marginBottom: 6,
            }}>&ldquo;</div>
            <div style={{
              fontFamily: 'monospace', fontSize: 15,
              color: 'rgba(244,245,248,0.82)',
              maxWidth: 900, lineHeight: 1.5,
            }}>{quoteText}</div>
            <div style={{
              fontFamily: 'monospace', fontSize: 12,
              color: BRAND.RED, marginTop: 8, letterSpacing: 1,
            }}>{quoteHandle}</div>
            <div style={{
              fontFamily: 'monospace', fontSize: 9, letterSpacing: 2,
              color: 'rgba(255,255,255,0.18)', marginTop: 4,
            }}>THOUGHT LEADER SIGNAL</div>
          </div>
        )}

        {/* Corner brackets - animated */}
        {/* Top-right */}
        <div style={{ position: 'absolute', right: 0, top: 0, opacity: bracketOpacity }}>
          <div style={{ width: 12, height: 2, background: BRAND.RED, position: 'absolute', right: 0, top: 0 }} />
          <div style={{ width: 2, height: 12, background: BRAND.RED, position: 'absolute', right: 0, top: 0 }} />
        </div>
        {/* Bottom-left */}
        <div style={{ position: 'absolute', left: 0, bottom: 0, opacity: bracketOpacity * 0.7 }}>
          <div style={{ width: 12, height: 2, background: BRAND.RED, position: 'absolute', left: 0, bottom: 0 }} />
          <div style={{ width: 2, height: 12, background: BRAND.RED, position: 'absolute', left: 0, bottom: 0 }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
