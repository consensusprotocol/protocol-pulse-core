import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  interpolate,
  Easing,
} from 'remotion';
import { BRAND, FONTS } from '../brand';

interface SocialCardProps {
  handle: string;
  text: string;
  likes: number;
  retweets: number;
  durationInFrames: number;
}

/**
 * Cyberpunk social card per PIPELINE_LAWS Section 19D.
 *
 * Glassmorphism card with animated scanlines, pulsing red dot,
 * slide-up entrance, hold, and fade-out exit.
 */
export const SocialCard: React.FC<SocialCardProps> = ({
  handle,
  text,
  likes,
  retweets,
  durationInFrames: _dur,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;

  // Card entrance: slide up + fade in (0.4s = 12 frames)
  const enterY = interpolate(frame, [0, 12], [100, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const enterOpacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Card exit: fade out (0.3s = 9 frames)
  const exitOpacity = interpolate(
    frame,
    [durationInFrames - 9, durationInFrames],
    [1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  // Pulse dot: opacity pulses 0.3 → 1.0 → 0.3 at 0.5s cycle
  const pulseOpacity = interpolate(
    Math.sin(t * Math.PI * 4),
    [-1, 1],
    [0.3, 1.0],
  );

  // Scanline scroll offset (scrolling upward slowly)
  const scanlineOffset = -(frame * 0.5) % 4;

  // Format numbers
  const formatNum = (n: number): string => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toLocaleString();
  };

  // Ticker scroll
  const tickerOffset = interpolate(frame, [0, 10000], [0, -8000], {
    extrapolateRight: 'extend',
  });

  // Word wrap text to ~55 chars per line, max 3 lines
  const wrapText = (str: string): string[] => {
    const words = str.split(' ');
    const lines: string[] = [];
    let current = '';
    for (const word of words) {
      if (current.length + word.length + 1 > 55) {
        lines.push(current);
        current = word;
        if (lines.length >= 3) break;
      } else {
        current = current ? `${current} ${word}` : word;
      }
    }
    if (current && lines.length < 3) lines.push(current);
    return lines;
  };
  const textLines = wrapText(text);

  const cardWidth = 1200;
  const cardHeight = 280;
  const cardX = (1920 - cardWidth) / 2;
  const cardY = 340;

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.BLACK }}>
      {/* Dark gradient background (matching WaveformVisualizer for consistency) */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(ellipse at 50% 40%, #0D0D0D 0%, ${BRAND.BLACK} 70%)`,
      }} />

      {/* Noise texture */}
      <div style={{
        position: 'absolute', inset: 0,
        opacity: 0.03,
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        backgroundSize: '256px 256px',
      }} />

      {/* Header text */}
      <div style={{
        position: 'absolute',
        top: 40,
        left: 0,
        right: 0,
        textAlign: 'center',
        color: BRAND.RED,
        fontSize: 28,
        fontWeight: 700,
        fontFamily: FONTS.BODY,
        letterSpacing: 2,
      }}>
        WHAT THE BITCOIN INTERNET IS SAYING
      </div>

      {/* Card container with entrance/exit animation */}
      <div style={{
        position: 'absolute',
        top: cardY,
        left: cardX,
        width: cardWidth,
        height: cardHeight,
        opacity: enterOpacity * exitOpacity,
        transform: `translateY(${enterY}px)`,
      }}>
        {/* Outer red glow */}
        <div style={{
          position: 'absolute',
          inset: -8,
          background: `rgba(204, 0, 0, 0.06)`,
          borderRadius: 4,
        }} />

        {/* Card body */}
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(15, 15, 15, 0.92)',
          border: `2px solid ${BRAND.RED}`,
          borderRadius: 2,
          overflow: 'hidden',
        }}>
          {/* Inner border (dark red glow effect) */}
          <div style={{
            position: 'absolute',
            inset: 3,
            border: `1px solid ${BRAND.DARK_RED}`,
            borderRadius: 1,
            pointerEvents: 'none',
          }} />

          {/* Animated scanlines */}
          <div style={{
            position: 'absolute',
            inset: 0,
            background: `repeating-linear-gradient(
              0deg,
              transparent,
              transparent 3px,
              rgba(0, 0, 0, 0.05) 3px,
              rgba(0, 0, 0, 0.05) 4px
            )`,
            transform: `translateY(${scanlineOffset}px)`,
            pointerEvents: 'none',
          }} />

          {/* Pulsing red dot */}
          <div style={{
            position: 'absolute',
            top: 18,
            left: 20,
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: BRAND.RED,
            opacity: pulseOpacity,
            boxShadow: `0 0 6px ${BRAND.RED}`,
          }} />

          {/* Handle */}
          <div style={{
            position: 'absolute',
            top: 14,
            left: 38,
            color: BRAND.RED,
            fontSize: 24,
            fontFamily: FONTS.MONO,
            fontWeight: 700,
          }}>
            @{handle}
          </div>

          {/* Tweet text */}
          <div style={{
            position: 'absolute',
            top: 54,
            left: 24,
            right: 24,
          }}>
            {textLines.map((line, i) => (
              <div key={i} style={{
                color: '#EDEDED',
                fontSize: 26,
                fontFamily: FONTS.BODY,
                lineHeight: '36px',
              }}>
                {line}
              </div>
            ))}
          </div>

          {/* Engagement stats bottom-left */}
          <div style={{
            position: 'absolute',
            bottom: 16,
            left: 24,
            display: 'flex',
            gap: 20,
            alignItems: 'center',
          }}>
            <span style={{
              color: BRAND.LIGHT_RED,
              fontSize: 18,
              fontFamily: FONTS.MONO,
            }}>
              ♥ {formatNum(likes)}
            </span>
            <span style={{
              color: BRAND.TEXT_SECONDARY,
              fontSize: 18,
              fontFamily: FONTS.MONO,
            }}>
              ↻ {formatNum(retweets)}
            </span>
          </div>

          {/* "via X" bottom-right */}
          <div style={{
            position: 'absolute',
            bottom: 18,
            right: 24,
            color: '#555555',
            fontSize: 14,
            fontFamily: FONTS.MONO,
          }}>
            via X
          </div>
        </div>
      </div>

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
          {'  PROTOCOL PULSE  |  PULSE CHECK  |  PROTOCOLPULSE.IO  '.repeat(10)}
        </span>
      </div>
    </AbsoluteFill>
  );
};
