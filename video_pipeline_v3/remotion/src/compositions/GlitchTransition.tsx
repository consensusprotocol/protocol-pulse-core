import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  interpolate,
  Easing,
} from 'remotion';
import { BRAND } from '../brand';

export const GlitchTransition: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const progress = frame / durationInFrames;

  // Flash intensity — peaks in the middle
  const flash = interpolate(
    frame,
    [0, durationInFrames * 0.3, durationInFrames * 0.5, durationInFrames * 0.7, durationInFrames],
    [0, 1, 0.3, 0.8, 0],
    { easing: Easing.out(Easing.quad) }
  );

  // Glitch scan lines
  const scanLineOffset = Math.sin(frame * 2.5) * 20;
  const glitchSlices = Array.from({ length: 8 }).map((_, i) => {
    const y = (i / 8) * 1080;
    const h = 1080 / 8;
    const xShift = Math.sin(frame * 3 + i * 1.7) * 40 * flash;
    return { y, h, xShift };
  });

  // RGB split
  const rgbOffset = flash * 12;

  // Noise bars
  const noiseBars = Array.from({ length: 20 }).map((_, i) => ({
    y: ((frame * 7 + i * 53) % 1080),
    height: 2 + Math.random() * 4,
    opacity: flash * 0.6,
  }));

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000' }}>
      {/* Base dark with red tint flash */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `rgba(204, 0, 0, ${flash * 0.15})`,
      }} />

      {/* Horizontal glitch slices */}
      {glitchSlices.map((slice, i) => (
        <div key={i} style={{
          position: 'absolute',
          top: slice.y, left: slice.xShift,
          width: 1920, height: slice.h,
          background: i % 2 === 0
            ? `rgba(204, 0, 0, ${flash * 0.1})`
            : `rgba(136, 0, 0, ${flash * 0.08})`,
        }} />
      ))}

      {/* Center flash burst */}
      <div style={{
        position: 'absolute',
        top: '50%', left: '50%',
        width: 400 * flash, height: 4,
        transform: 'translate(-50%, -50%)',
        background: `rgba(255, 255, 255, ${flash * 0.9})`,
        boxShadow: `0 0 ${80 * flash}px ${40 * flash}px rgba(204, 0, 0, ${flash * 0.5})`,
      }} />

      {/* Noise bars */}
      {noiseBars.map((bar, i) => (
        <div key={i} style={{
          position: 'absolute',
          top: bar.y, left: 0, right: 0,
          height: bar.height,
          background: `rgba(255, 255, 255, ${bar.opacity})`,
        }} />
      ))}

      {/* Scan line overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `repeating-linear-gradient(
          0deg,
          transparent,
          transparent 2px,
          rgba(0,0,0,0.15) 2px,
          rgba(0,0,0,0.15) 4px
        )`,
        transform: `translateY(${scanLineOffset}px)`,
        opacity: flash * 0.5,
      }} />
    </AbsoluteFill>
  );
};
