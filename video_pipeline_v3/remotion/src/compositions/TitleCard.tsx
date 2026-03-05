import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  AbsoluteFill,
  Img,
  staticFile,
  interpolate,
  Easing,
  spring,
} from 'remotion';
import { BRAND, FONTS } from '../brand';

interface TitleCardProps {
  title: string;
  date: string;
  durationInFrames: number;
}

/**
 * Episode title card per PIPELINE_LAWS Section 19E.
 *
 * 120 frames (4 seconds at 30fps):
 * - Frame 0-30: Logo fades in with spring scale 0.8→1.0
 * - Frame 45: Episode title slides up + fades in
 * - Frame 60: Date + "PULSE CHECK" fades in
 * - Frame 75: EKG heartbeat pulse line sweeps across bottom
 * - Background: animated dark gradient with moving red accent light
 */
export const TitleCard: React.FC<TitleCardProps> = ({
  title,
  date,
  durationInFrames: _dur,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Red accent light source slowly moves
  const lightX = interpolate(frame, [0, durationInFrames], [30, 70], {
    extrapolateRight: 'clamp',
  });
  const lightY = interpolate(frame, [0, durationInFrames], [35, 45], {
    extrapolateRight: 'clamp',
  });

  // Logo: spring scale-in (frame 0-30)
  const logoSpring = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 80, mass: 0.8 },
  });
  const logoScale = interpolate(logoSpring, [0, 1], [0.8, 1]);
  const logoOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // Title: fade in + slide at frame 45
  const titleOpacity = interpolate(frame, [45, 60], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const titleY = interpolate(frame, [45, 60], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  // Date + PULSE CHECK: fade in at frame 60
  const dateOpacity = interpolate(frame, [60, 75], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // EKG pulse line sweep at frame 75
  const ekgProgress = interpolate(frame, [75, 105], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  // Generate EKG path
  const generateEkgPath = (): string => {
    const width = 1920;
    const midY = 25;
    const points: string[] = [];

    const drawTo = ekgProgress * width;

    for (let x = 0; x <= drawTo; x += 2) {
      const pos = x / width;
      let y = midY;

      // Two heartbeat pulses across the width
      for (let beat = 0; beat < 2; beat++) {
        const center = 0.3 + beat * 0.4;
        const local = pos - center;

        if (Math.abs(local) < 0.08) {
          const phase = (local + 0.08) / 0.16;
          if (phase > 0.3 && phase < 0.45) {
            y -= Math.sin((phase - 0.3) / 0.15 * Math.PI) * 35;
          } else if (phase > 0.45 && phase < 0.55) {
            y += Math.sin((phase - 0.45) / 0.1 * Math.PI) * 10;
          } else if (phase > 0.55 && phase < 0.7) {
            y -= Math.sin((phase - 0.55) / 0.15 * Math.PI) * 15;
          }
        }
      }

      points.push(`${x === 0 ? 'M' : 'L'} ${x} ${y}`);
    }

    return points.join(' ');
  };

  const ekgPath = generateEkgPath();

  // Global fade-out at end
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  return (
    <AbsoluteFill style={{
      backgroundColor: BRAND.BLACK,
      opacity: fadeOut,
    }}>
      {/* Animated background with moving red accent light */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(ellipse at ${lightX}% ${lightY}%, ${BRAND.BG_GRADIENT_START} 0%, ${BRAND.BLACK} 60%)`,
      }} />

      {/* Subtle red radial accent */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(circle at ${lightX}% ${lightY}%, rgba(204, 0, 0, 0.04) 0%, transparent 50%)`,
      }} />

      {/* Logo — spring scale-in, centered */}
      <div style={{
        position: 'absolute',
        top: 200,
        left: '50%',
        transform: `translateX(-50%) scale(${logoScale})`,
        opacity: logoOpacity,
      }}>
        <Img
          src={staticFile('logo_protocol_pulse.png')}
          style={{
            height: 350,
            width: 'auto',
            filter: 'drop-shadow(0 0 40px rgba(204, 0, 0, 0.3))',
          }}
        />
      </div>

      {/* Episode title */}
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
          color: BRAND.WHITE,
          fontSize: 34,
          fontWeight: 700,
          fontFamily: FONTS.BODY,
          letterSpacing: 1,
          padding: '0 120px',
        }}>
          {title}
        </div>
      </div>

      {/* Date + PULSE CHECK */}
      <div style={{
        position: 'absolute',
        top: 660,
        left: 0,
        right: 0,
        textAlign: 'center',
        opacity: dateOpacity,
      }}>
        <span style={{
          color: BRAND.RED,
          fontSize: 18,
          fontFamily: FONTS.MONO,
          letterSpacing: 2,
        }}>
          {date} &nbsp;•&nbsp; PULSE CHECK
        </span>
      </div>

      {/* EKG heartbeat pulse line sweeping across bottom */}
      {ekgProgress > 0 && (
        <svg
          style={{
            position: 'absolute',
            bottom: 80,
            left: 0,
          }}
          width={1920}
          height={50}
          viewBox="0 0 1920 50"
        >
          {/* Glow */}
          <path
            d={ekgPath}
            fill="none"
            stroke={BRAND.RED}
            strokeWidth={5}
            strokeLinecap="round"
            opacity={0.3}
            filter="blur(3px)"
          />
          {/* Main line */}
          <path
            d={ekgPath}
            fill="none"
            stroke={BRAND.RED}
            strokeWidth={2}
            strokeLinecap="round"
          />
          {/* Leading dot */}
          {ekgProgress < 1 && (
            <circle
              cx={ekgProgress * 1920}
              cy={25}
              r={4}
              fill={BRAND.LIGHT_RED}
            />
          )}
        </svg>
      )}
    </AbsoluteFill>
  );
};
