import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  Img,
  staticFile,
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
 * Matches PIPELINE_LAWS Section 19B:
 * - Dark gradient mesh background with noise texture
 * - Centered logo with subtle pulse animation
 * - Designed heartbeat-style waveform (not raw audio)
 * - Episode title, corner elements, gold bottom bar
 * - Floating red particle effects
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

  // Logo pulse: scale oscillates 1.0 → 1.02 on a 3-second sine cycle
  const logoScale = interpolate(
    Math.sin((t / 3) * Math.PI * 2),
    [-1, 1],
    [1.0, 1.02],
  );

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
  const waveWidth = 960;
  const waveHeight = 60;
  const generateHeartbeatPath = (): string => {
    const points: string[] = [];
    const segments = 200;
    const drawProgress = interpolate(frame, [0, 45], [0, 1], {
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.quad),
    });

    for (let i = 0; i <= segments * drawProgress; i++) {
      const x = (i / segments) * waveWidth;
      const phase = (i / segments) * Math.PI * 8 + t * 2;

      // Base flat line with periodic heartbeat spikes
      let y = waveHeight / 2;
      const beatPhase = ((i / segments) * 4 + t * 0.5) % 1;

      if (beatPhase > 0.35 && beatPhase < 0.45) {
        // Sharp upward spike (P wave)
        const spike = Math.sin((beatPhase - 0.35) / 0.1 * Math.PI);
        y -= spike * 15;
      } else if (beatPhase > 0.45 && beatPhase < 0.5) {
        // Sharp downward (Q)
        const dip = Math.sin((beatPhase - 0.45) / 0.05 * Math.PI);
        y += dip * 8;
      } else if (beatPhase > 0.5 && beatPhase < 0.58) {
        // Tall upward spike (QRS complex)
        const spike = Math.sin((beatPhase - 0.5) / 0.08 * Math.PI);
        y -= spike * (waveHeight * 0.8);
      } else if (beatPhase > 0.58 && beatPhase < 0.65) {
        // Recovery dip (S wave)
        const dip = Math.sin((beatPhase - 0.58) / 0.07 * Math.PI);
        y += dip * 12;
      } else if (beatPhase > 0.7 && beatPhase < 0.8) {
        // T wave (gentle bump)
        const bump = Math.sin((beatPhase - 0.7) / 0.1 * Math.PI);
        y -= bump * 10;
      } else {
        // Slight baseline wobble
        y += Math.sin(phase * 0.5) * 1.5;
      }

      points.push(`${i === 0 ? 'M' : 'L'} ${x} ${y}`);
    }
    return points.join(' ');
  };

  const waveformPath = generateHeartbeatPath();

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

      {/* Centered logo with pulse animation */}
      <div style={{
        position: 'absolute',
        top: 120,
        left: '50%',
        transform: `translateX(-50%) scale(${logoScale})`,
      }}>
        <Img
          src={staticFile('logo_protocol_pulse.png')}
          style={{
            height: 250,
            width: 'auto',
            filter: 'drop-shadow(0 0 20px rgba(204, 0, 0, 0.3))',
          }}
        />
      </div>

      {/* Heartbeat waveform — main line */}
      <svg
        style={{
          position: 'absolute',
          top: 480,
          left: (1920 - waveWidth) / 2,
          overflow: 'visible',
        }}
        width={waveWidth}
        height={waveHeight}
        viewBox={`0 0 ${waveWidth} ${waveHeight}`}
      >
        {/* Glow layer */}
        <path
          d={waveformPath}
          fill="none"
          stroke={BRAND.RED}
          strokeWidth={6}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.3}
          filter="blur(4px)"
        />
        {/* Main line */}
        <path
          d={waveformPath}
          fill="none"
          stroke={BRAND.RED}
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* Mirror reflection waveform */}
      <svg
        style={{
          position: 'absolute',
          top: 542,
          left: (1920 - waveWidth) / 2,
          overflow: 'visible',
          transform: 'scaleY(-1)',
          opacity: 0.3,
          filter: 'blur(1px)',
        }}
        width={waveWidth}
        height={30}
        viewBox={`0 0 ${waveWidth} ${waveHeight}`}
      >
        <path
          d={waveformPath}
          fill="none"
          stroke={BRAND.DARK_RED}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* Episode title below waveform */}
      <div style={{
        position: 'absolute',
        top: 600,
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

      {/* Bottom gold info bar */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 50,
        backgroundColor: BRAND.BLACK,
        borderTop: `1px solid ${BRAND.BORDER}`,
        display: 'flex',
        alignItems: 'center',
        overflow: 'hidden',
      }}>
        <span style={{
          color: BRAND.GOLD,
          fontSize: 14,
          fontFamily: FONTS.MONO,
          whiteSpace: 'nowrap',
          transform: `translateX(${tickerOffset}px)`,
        }}>
          {tickerText.repeat(10)}
        </span>
      </div>
    </AbsoluteFill>
  );
};
