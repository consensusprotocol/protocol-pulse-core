import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  interpolate,
  Easing,
} from 'remotion';
import { BRAND } from '../brand';

export const TitleCard: React.FC<{
  title: string;
  btcPrice: string;
}> = ({ title, btcPrice }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Fade in
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // Fade out
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    { extrapolateLeft: 'clamp' }
  );

  // Title slide in from left
  const titleX = interpolate(frame, [5, 25], [-200, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // Subtitle slide in
  const subtitleX = interpolate(frame, [12, 32], [-200, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // Left bar height animation
  const barHeight = interpolate(frame, [0, 20], [0, 1080], {
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // Accent line width
  const lineWidth = interpolate(frame, [8, 28], [0, 1920], {
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{
      backgroundColor: BRAND.BG_GRADIENT_END,
      opacity: opacity * fadeOut,
    }}>
      {/* Background gradient */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `linear-gradient(135deg, ${BRAND.BG_GRADIENT_START} 0%, ${BRAND.BG_GRADIENT_MID} 50%, ${BRAND.BG_GRADIENT_END} 100%)`,
      }} />

      {/* Animated left accent bar */}
      <div style={{
        position: 'absolute', left: 0, top: 0,
        width: 6, height: barHeight,
        background: `linear-gradient(180deg, ${BRAND.RED}, ${BRAND.DARK_RED})`,
      }} />

      {/* Center accent line */}
      <div style={{
        position: 'absolute', top: 540, left: (1920 - lineWidth) / 2,
        width: lineWidth, height: 2,
        background: 'rgba(204, 0, 0, 0.4)',
      }} />

      {/* PROTOCOL PULSE branding */}
      <div style={{
        position: 'absolute', top: 280, left: 0, right: 0,
        textAlign: 'center',
        transform: `translateX(${titleX}px)`,
      }}>
        <div style={{
          color: BRAND.RED, fontSize: 82, fontWeight: 700,
          fontFamily: 'DejaVu Sans, sans-serif',
          letterSpacing: 4,
          textShadow: '0 0 40px rgba(204,0,0,0.3)',
        }}>
          PROTOCOL PULSE
        </div>
      </div>

      {/* Episode title */}
      <div style={{
        position: 'absolute', top: 420, left: 0, right: 0,
        textAlign: 'center',
        transform: `translateX(${subtitleX}px)`,
      }}>
        <div style={{
          color: BRAND.WHITE, fontSize: 42, fontWeight: 700,
          fontFamily: 'DejaVu Sans, sans-serif',
          opacity: 0.9,
          padding: '0 120px',
        }}>
          {title}
        </div>
      </div>

      {/* BTC Price badge */}
      <div style={{
        position: 'absolute', bottom: 120, left: 0, right: 0,
        textAlign: 'center',
        transform: `translateX(${subtitleX}px)`,
      }}>
        <span style={{
          color: BRAND.GOLD, fontSize: 28,
          fontFamily: 'DejaVu Sans Mono, monospace',
          background: 'rgba(10,10,10,0.8)',
          padding: '8px 24px', borderRadius: 4,
        }}>
          BTC {btcPrice}
        </span>
      </div>

      {/* Bottom ticker bar */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 44, background: BRAND.TICKER_BG,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{
          color: BRAND.GOLD, fontSize: 16,
          fontFamily: 'DejaVu Sans Mono, monospace',
        }}>
          PROTOCOLPULSE.IO
        </span>
      </div>
    </AbsoluteFill>
  );
};
