import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  interpolate,
  Easing,
} from 'remotion';
import { BRAND } from '../brand';

/**
 * Alpha-channel glitch transition (21 frames / 0.7s at 30fps).
 *
 * Renders on a TRANSPARENT background. Red scan lines sweep left-to-right,
 * revealing transparency behind them. Glitch artifacts (red pixel blocks,
 * white flashes) appear during the sweep. Residual particles fade in the
 * last 6 frames.
 *
 * Designed to overlay between outgoing and incoming clips:
 *   outgoing → transition (alpha) → incoming shows through transparent areas.
 */
export const GlitchTransition: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Sweep progress: 0→1 over first 15 frames (0.5s), then hold
  const sweepProgress = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });

  // Fade-out for residual particles (frames 15-21)
  const residualFade = interpolate(frame, [15, durationInFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Flash intensity peaks mid-sweep
  const flash = interpolate(
    frame,
    [0, 5, 10, 15, durationInFrames],
    [0, 0.8, 1, 0.4, 0],
    { extrapolateRight: 'clamp' }
  );

  // Generate scan line positions (8 horizontal bands sweeping left to right)
  const scanLines = Array.from({ length: 12 }).map((_, i) => {
    const bandY = (i / 12) * 1080;
    const bandH = 1080 / 12;
    // Stagger: each band starts slightly after the previous
    const stagger = i * 0.06;
    const bandProgress = interpolate(
      sweepProgress,
      [stagger, Math.min(stagger + 0.4, 1)],
      [0, 1],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
    );
    // Glitch offset: horizontal jitter during sweep
    const jitter = Math.sin(frame * 4.5 + i * 2.3) * 30 * (1 - bandProgress) * flash;
    return { y: bandY, h: bandH, progress: bandProgress, jitter };
  });

  // Glitch pixel blocks (random red rectangles)
  const glitchBlocks = Array.from({ length: 15 }).map((_, i) => {
    const seed = i * 7.31 + frame * 0.37;
    const x = ((Math.sin(seed * 1.7) * 0.5 + 0.5) * 1920);
    const y = ((Math.sin(seed * 2.3) * 0.5 + 0.5) * 1080);
    const w = 20 + Math.abs(Math.sin(seed * 3.1)) * 80;
    const h = 2 + Math.abs(Math.sin(seed * 4.7)) * 8;
    const opacity = flash * (Math.sin(seed * 5.9) * 0.5 + 0.5) * 0.7;
    const isWhite = i % 7 === 0;
    return { x, y, w, h, opacity, isWhite };
  });

  // Residual particles (small dots that linger after sweep)
  const particles = Array.from({ length: 8 }).map((_, i) => {
    const seed = i * 13.7;
    const x = (Math.sin(seed + frame * 0.1) * 0.5 + 0.5) * 1920;
    const y = (Math.cos(seed * 1.3 + frame * 0.08) * 0.5 + 0.5) * 1080;
    const size = 3 + Math.abs(Math.sin(seed)) * 5;
    return { x, y, size, opacity: residualFade * 0.6 };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent' }}>
      {/* Scan line sweep bands — each band transitions from opaque to transparent */}
      {scanLines.map((line, i) => (
        <div key={`scan-${i}`} style={{
          position: 'absolute',
          top: line.y,
          left: line.jitter,
          width: 1920,
          height: line.h,
          background: `linear-gradient(to right,
            ${BRAND.RED}${Math.round((1 - line.progress) * 255).toString(16).padStart(2, '0')} 0%,
            ${BRAND.DARK_RED}${Math.round((1 - line.progress) * 180).toString(16).padStart(2, '0')} ${line.progress * 100}%,
            transparent ${Math.min(line.progress * 100 + 20, 100)}%
          )`,
        }} />
      ))}

      {/* Center flash burst during peak */}
      {flash > 0.1 && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: `${sweepProgress * 100}%`,
          width: 6,
          height: 1080,
          transform: 'translate(-50%, -50%)',
          background: `rgba(255, 255, 255, ${flash * 0.6})`,
          boxShadow: `0 0 ${60 * flash}px ${20 * flash}px ${BRAND.RED}88`,
        }} />
      )}

      {/* Glitch pixel blocks */}
      {glitchBlocks.map((block, i) => (
        block.opacity > 0.05 && (
          <div key={`block-${i}`} style={{
            position: 'absolute',
            left: block.x,
            top: block.y,
            width: block.w,
            height: block.h,
            backgroundColor: block.isWhite
              ? `rgba(255, 255, 255, ${block.opacity})`
              : `rgba(204, 0, 0, ${block.opacity})`,
          }} />
        )
      ))}

      {/* Horizontal noise lines during sweep */}
      {flash > 0.2 && Array.from({ length: 6 }).map((_, i) => {
        const noiseY = ((frame * 11 + i * 173) % 1080);
        return (
          <div key={`noise-${i}`} style={{
            position: 'absolute',
            top: noiseY,
            left: 0,
            right: 0,
            height: 1,
            backgroundColor: `rgba(255, 68, 68, ${flash * 0.3})`,
          }} />
        );
      })}

      {/* Residual red particles after sweep completes */}
      {sweepProgress >= 0.9 && particles.map((p, i) => (
        <div key={`particle-${i}`} style={{
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
