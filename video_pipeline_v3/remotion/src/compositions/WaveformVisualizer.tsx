import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  interpolate,
  Easing,
} from 'remotion';
import { BRAND, FONTS } from '../brand';

interface WaveformVisualizerProps {
  title: string;
  btcPrice: string;
  date: string;
  durationInFrames: number;
}

/**
 * Broadcast-quality waveform visualizer for narration segments.
 *
 * Per OVERNIGHT_BUILD_PROMPT:
 * - NO LOGO (logo restraint rule — max 3 appearances per episode)
 * - Transparent bg or renders with CyberpunkBackground
 * - Designed heartbeat/EKG waveform (not raw audio)
 * - Neon glow on the line
 * - Traveling dot with trail effect
 * - Mirror reflection below
 * - Bottom gold info bar with BTC price
 */
export const WaveformVisualizer: React.FC<WaveformVisualizerProps> = ({
  title,
  btcPrice,
  date,
  durationInFrames: _dur,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;

  // Title fade-in at frame 15
  const titleOpacity = interpolate(frame, [15, 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const titleY = interpolate(frame, [15, 30], [10, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // Generate heartbeat waveform path (EKG-style, not raw audio)
  const waveWidth = 800;
  const waveHeight = 50;
  const generateHeartbeatPath = (): string => {
    const points: string[] = [];
    const segments = 200;
    const drawProgress = interpolate(frame, [0, durationInFrames], [0, 1], {
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.quad),
    });

    for (let i = 0; i <= segments * drawProgress; i++) {
      const x = (i / segments) * waveWidth;

      // Base flat line with periodic heartbeat spikes
      let y = waveHeight / 2;
      const beatPhase = ((i / segments) * 4 + t * 0.5) % 1;

      if (beatPhase > 0.35 && beatPhase < 0.45) {
        const spike = Math.sin((beatPhase - 0.35) / 0.1 * Math.PI);
        y -= spike * 12;
      } else if (beatPhase > 0.45 && beatPhase < 0.5) {
        const dip = Math.sin((beatPhase - 0.45) / 0.05 * Math.PI);
        y += dip * 6;
      } else if (beatPhase > 0.5 && beatPhase < 0.58) {
        const spike = Math.sin((beatPhase - 0.5) / 0.08 * Math.PI);
        y -= spike * (waveHeight * 0.8);
      } else if (beatPhase > 0.58 && beatPhase < 0.65) {
        const dip = Math.sin((beatPhase - 0.58) / 0.07 * Math.PI);
        y += dip * 10;
      } else if (beatPhase > 0.7 && beatPhase < 0.8) {
        const bump = Math.sin((beatPhase - 0.7) / 0.1 * Math.PI);
        y -= bump * 8;
      } else {
        y += Math.sin(((i / segments) * Math.PI * 8 + t * 2) * 0.5) * 1.5;
      }

      points.push(`${i === 0 ? 'M' : 'L'} ${x} ${y}`);
    }
    return points.join(' ');
  };

  const waveformPath = generateHeartbeatPath();

  // Trace dot position — follows the last drawn point on the waveform
  const traceProgress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });
  const traceSegment = Math.floor(traceProgress * 200);
  const traceX = (traceSegment / 200) * waveWidth;
  const traceBeatPhase = ((traceSegment / 200) * 4 + t * 0.5) % 1;
  let traceY = waveHeight / 2;
  if (traceBeatPhase > 0.5 && traceBeatPhase < 0.58) {
    const spike = Math.sin((traceBeatPhase - 0.5) / 0.08 * Math.PI);
    traceY -= spike * (waveHeight * 0.8);
  }

  // Trail dots (2-3 previous positions at decreasing opacity)
  const trailDots = [1, 2, 3].map((offset) => {
    const seg = Math.max(0, traceSegment - offset * 3);
    const tx = (seg / 200) * waveWidth;
    const tBeatPhase = ((seg / 200) * 4 + t * 0.5) % 1;
    let ty = waveHeight / 2;
    if (tBeatPhase > 0.5 && tBeatPhase < 0.58) {
      const spike = Math.sin((tBeatPhase - 0.5) / 0.08 * Math.PI);
      ty -= spike * (waveHeight * 0.8);
    }
    return { x: tx, y: ty, opacity: 0.6 - offset * 0.15 };
  });

  // Floating red particles (3-5 dots)
  const particles = Array.from({ length: 4 }).map((_, i) => {
    const seed = i * 17.3;
    const px = 200 + Math.sin(seed + t * 0.15) * 760 + 480;
    const py = 200 + Math.cos(seed * 1.7 + t * 0.1) * 400;
    return { x: px, y: py };
  });

  // Bottom bar ticker scroll
  const tickerOffset = interpolate(frame, [0, 10000], [0, -8000], {
    extrapolateRight: 'extend',
  });
  const tickerText = `  PROTOCOL PULSE  |  PULSE CHECK  |  BTC ${btcPrice}  |  PROTOCOLPULSE.IO  `;

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.BLACK }}>
      {/* Dark gradient mesh background */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(ellipse at 50% 40%, #0D0D0D 0%, ${BRAND.BLACK} 70%)`,
      }} />

      {/* Subtle noise texture overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        opacity: 0.03,
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        backgroundSize: '256px 256px',
      }} />

      {/* Corner: date top-left */}
      <div style={{
        position: 'absolute', top: 16, left: 20,
        color: BRAND.TEXT_DIM, fontSize: 14, letterSpacing: 2,
        fontFamily: FONTS.MONO,
      }}>
        {date}
      </div>

      {/* Corner: "PROTOCOL PULSE" top-right */}
      <div style={{
        position: 'absolute', top: 16, right: 20,
        color: BRAND.TEXT_DIM, fontSize: 14, letterSpacing: 4,
        fontFamily: FONTS.MONO,
      }}>
        PROTOCOL PULSE
      </div>

      {/* NO LOGO — per logo restraint rule, max 3 appearances per episode.
          Logo appears in: TitleCard, LowerThird, Outro only. */}

      {/* Heartbeat waveform — main line, 800px centered */}
      <svg
        style={{
          position: 'absolute',
          top: 490,
          left: (1920 - waveWidth) / 2,
          overflow: 'visible',
        }}
        width={waveWidth}
        height={waveHeight}
        viewBox={`0 0 ${waveWidth} ${waveHeight}`}
      >
        {/* Neon glow layer (blur copy behind main line) */}
        <path
          d={waveformPath}
          fill="none"
          stroke={BRAND.RED}
          strokeWidth={8}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.4}
          style={{ filter: 'blur(6px)' }}
        />
        {/* Main crisp line */}
        <path
          d={waveformPath}
          fill="none"
          stroke={BRAND.RED}
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Trail dots */}
        {traceProgress > 0.02 && trailDots.map((dot, i) => (
          <circle
            key={`trail-${i}`}
            cx={dot.x}
            cy={dot.y}
            r={4 - i * 0.5}
            fill={BRAND.WHITE}
            opacity={dot.opacity}
          />
        ))}
        {/* Traveling dot — white, 6px */}
        {traceProgress > 0 && traceProgress < 1 && (
          <circle
            cx={traceX}
            cy={traceY}
            r={6}
            fill={BRAND.WHITE}
            opacity={0.9}
          />
        )}
      </svg>

      {/* Mirror reflection waveform — below main, flipped, blurred */}
      <svg
        style={{
          position: 'absolute',
          top: 542,
          left: (1920 - waveWidth) / 2,
          overflow: 'visible',
          transform: 'scaleY(-1)',
          opacity: 0.15,
          filter: 'blur(2px)',
        }}
        width={waveWidth}
        height={25}
        viewBox={`0 0 ${waveWidth} ${waveHeight}`}
      >
        <path
          d={waveformPath}
          fill="none"
          stroke={BRAND.RED}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* Episode title below waveform */}
      <div style={{
        position: 'absolute',
        top: 590,
        left: 0,
        right: 0,
        textAlign: 'center',
        opacity: titleOpacity,
        transform: `translateY(${titleY}px)`,
      }}>
        <div style={{
          color: '#EDEDED',
          fontSize: 24,
          letterSpacing: 2,
          fontFamily: FONTS.BODY,
          fontWeight: 400,
        }}>
          {title}
        </div>
      </div>

      {/* Floating red particles */}
      {particles.map((p, i) => (
        <div key={i} style={{
          position: 'absolute',
          left: p.x,
          top: p.y,
          width: 4,
          height: 4,
          borderRadius: '50%',
          backgroundColor: BRAND.RED,
          opacity: 0.15,
        }} />
      ))}

      {/* Bottom gold info bar — 44px, full width */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 44,
        backgroundColor: 'rgba(10,10,10,0.9)',
        borderTop: `1px solid ${BRAND.BORDER}`,
        display: 'flex',
        alignItems: 'center',
        overflow: 'hidden',
      }}>
        <span style={{
          color: BRAND.GOLD,
          fontSize: 13,
          fontFamily: FONTS.MONO,
          letterSpacing: 2,
          whiteSpace: 'nowrap',
          transform: `translateX(${tickerOffset}px)`,
        }}>
          {tickerText.repeat(10)}
        </span>
      </div>
    </AbsoluteFill>
  );
};
