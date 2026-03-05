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

interface LowerThirdProps {
  channelName: string;
  speakerName?: string;
  durationInFrames: number;
}

/**
 * Lower third overlay per PIPELINE_LAWS Section 19F.
 *
 * Transparent background — renders as WebM with alpha for overlay on clips.
 * Shows channel name + optional speaker name with Protocol Pulse logo.
 * Slides in from left, holds 5 seconds, fades out.
 */
export const LowerThird: React.FC<LowerThirdProps> = ({
  channelName,
  speakerName,
  durationInFrames: _dur,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Slide in from left (0.3s = 9 frames)
  const enterX = interpolate(frame, [0, 9], [-300, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const enterOpacity = interpolate(frame, [0, 9], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Fade out (0.2s = 6 frames)
  const exitOpacity = interpolate(
    frame,
    [durationInFrames - 6, durationInFrames],
    [1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent' }}>
      {/* Bottom 120px region */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 120,
        background: 'linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.85) 100%)',
        opacity: enterOpacity * exitOpacity,
        transform: `translateX(${enterX}px)`,
      }}>
        {/* Content container */}
        <div style={{
          position: 'absolute',
          bottom: 20,
          left: 40,
          display: 'flex',
          alignItems: 'center',
          gap: 16,
        }}>
          {/* Small Protocol Pulse logo */}
          <Img
            src={staticFile('logo_protocol_pulse.png')}
            style={{
              height: 50,
              width: 'auto',
              filter: 'drop-shadow(0 0 8px rgba(204, 0, 0, 0.4))',
            }}
          />

          {/* Text block */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Channel name */}
            <div style={{
              color: BRAND.WHITE,
              fontSize: 22,
              fontWeight: 700,
              fontFamily: FONTS.BODY,
              textShadow: '0 2px 4px rgba(0,0,0,0.5)',
            }}>
              {channelName}
            </div>

            {/* Speaker name (if provided) */}
            {speakerName && (
              <div style={{
                color: BRAND.RED,
                fontSize: 18,
                fontFamily: FONTS.BODY,
                textShadow: '0 1px 3px rgba(0,0,0,0.5)',
              }}>
                {speakerName}
              </div>
            )}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
