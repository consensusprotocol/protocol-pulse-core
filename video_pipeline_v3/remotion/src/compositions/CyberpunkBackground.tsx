import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  interpolate,
} from 'remotion';
import { BRAND } from '../brand';

interface CyberpunkBackgroundProps {
  durationInFrames: number;
}

/**
 * Seamlessly looping cyberpunk background for narration segments.
 *
 * - Dark gradient mesh with slow movement
 * - Floating red particles (10-15% opacity, slow drift)
 * - Faint grid lines (2% opacity, perspective vanishing point)
 * - Scanning red line (slow top-to-bottom sweep, 8% opacity)
 * - Noise texture overlay at 3% opacity
 */
export const CyberpunkBackground: React.FC<CyberpunkBackgroundProps> = ({
  durationInFrames: _dur,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;

  // Gradient mesh movement — slow drift
  const gradX = interpolate(
    Math.sin(t * 0.1 * Math.PI),
    [-1, 1],
    [40, 60],
  );
  const gradY = interpolate(
    Math.cos(t * 0.07 * Math.PI),
    [-1, 1],
    [35, 50],
  );

  // Scanning line — sweeps top to bottom over 10 seconds, loops
  const scanY = ((t * 108) % 1080);

  // Grid perspective lines — vanishing point at center-top
  const gridLines = Array.from({ length: 20 }).map((_, i) => {
    const y = 200 + i * 50;
    return y;
  });

  // Vertical grid lines fanning from vanishing point
  const vLines = Array.from({ length: 12 }).map((_, i) => {
    const angle = ((i - 5.5) / 11) * 0.6;
    return angle;
  });

  // Floating particles (8 dots, slow drift)
  const particles = Array.from({ length: 8 }).map((_, i) => {
    const seed = i * 23.7;
    const px = interpolate(
      Math.sin(seed + t * 0.08),
      [-1, 1],
      [100, 1820],
    );
    const py = interpolate(
      Math.cos(seed * 1.3 + t * 0.06),
      [-1, 1],
      [100, 980],
    );
    const size = 3 + Math.abs(Math.sin(seed * 2.1)) * 4;
    const opacity = interpolate(
      Math.sin(seed * 3.7 + t * 0.3),
      [-1, 1],
      [0.06, 0.15],
    );
    return { x: px, y: py, size, opacity };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.BLACK }}>
      {/* Moving dark gradient mesh */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(ellipse at ${gradX}% ${gradY}%, ${BRAND.BG_GRADIENT_START} 0%, ${BRAND.BG_GRADIENT_MID} 40%, ${BRAND.BLACK} 80%)`,
      }} />

      {/* Secondary subtle red accent */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(circle at ${100 - gradX}% ${gradY + 20}%, rgba(204, 0, 0, 0.03) 0%, transparent 50%)`,
      }} />

      {/* Noise texture overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        opacity: 0.03,
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        backgroundSize: '256px 256px',
      }} />

      {/* Perspective grid — horizontal lines */}
      <svg style={{ position: 'absolute', inset: 0 }} width={1920} height={1080} viewBox="0 0 1920 1080">
        {gridLines.map((y, i) => (
          <line
            key={`h-${i}`}
            x1={0} y1={y} x2={1920} y2={y}
            stroke={BRAND.RED}
            strokeWidth={0.5}
            opacity={0.02}
          />
        ))}
        {/* Vertical lines from vanishing point (960, 150) */}
        {vLines.map((angle, i) => {
          const x2 = 960 + Math.tan(angle) * 930;
          return (
            <line
              key={`v-${i}`}
              x1={960} y1={150}
              x2={x2} y2={1080}
              stroke={BRAND.RED}
              strokeWidth={0.5}
              opacity={0.02}
            />
          );
        })}
      </svg>

      {/* Scanning red line — slow sweep */}
      <div style={{
        position: 'absolute',
        top: scanY,
        left: 0,
        right: 0,
        height: 2,
        background: `linear-gradient(to right, transparent 0%, ${BRAND.RED} 30%, ${BRAND.RED} 70%, transparent 100%)`,
        opacity: 0.08,
        boxShadow: `0 0 20px 4px rgba(204, 0, 0, 0.06)`,
      }} />

      {/* Floating red particles */}
      {particles.map((p, i) => (
        <div key={i} style={{
          position: 'absolute',
          left: p.x,
          top: p.y,
          width: p.size,
          height: p.size,
          borderRadius: '50%',
          backgroundColor: BRAND.RED,
          opacity: p.opacity,
        }} />
      ))}
    </AbsoluteFill>
  );
};
