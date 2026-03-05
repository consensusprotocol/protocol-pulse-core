import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  Audio,
  staticFile,
  AbsoluteFill,
  interpolate,
} from 'remotion';
import { BRAND } from '../brand';

export const WaveformVisualizer: React.FC<{
  audioFile: string;
  speakerName: string;
  speakerColor: string;
  btcPrice: string;
  thumbnailFile?: string;
}> = ({ audioFile, speakerName, speakerColor, btcPrice, thumbnailFile }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Generate pseudo-waveform bars from frame number
  const barCount = 120;
  const bars = Array.from({ length: barCount }).map((_, i) => {
    const phase = (frame / fps) * 3 + i * 0.15;
    const amplitude = (Math.sin(phase) * 0.4 + 0.5) *
      (Math.sin(phase * 0.7 + i * 0.3) * 0.3 + 0.7);
    return Math.max(0.05, Math.min(1, amplitude));
  });

  const tickerOffset = interpolate(frame, [0, 10000], [0, -8000], {
    extrapolateRight: 'extend',
  });
  const tickerText = `  PROTOCOL PULSE  |  PULSE CHECK  |  BTC ${btcPrice}  |  PROTOCOLPULSE.IO  `;

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.BG_DARK }}>
      {/* Deep space gradient background */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `linear-gradient(180deg, ${BRAND.BG_GRADIENT_START} 0%, ${BRAND.BG_GRADIENT_MID} 50%, ${BRAND.BG_GRADIENT_END} 100%)`,
      }} />

      {/* Center accent line */}
      <div style={{
        position: 'absolute', top: 538, left: 0, right: 0,
        height: 2, background: 'rgba(204, 0, 0, 0.35)',
      }} />
      <div style={{
        position: 'absolute', top: 542, left: 0, right: 0,
        height: 1, background: 'rgba(136, 0, 0, 0.2)',
      }} />

      {/* Left accent bar */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0,
        width: 4, background: 'rgba(204, 0, 0, 0.6)',
      }} />

      {/* Waveform bars (mirrored) */}
      <div style={{
        position: 'absolute', top: 380, left: 60, right: 60,
        height: 320, display: 'flex', alignItems: 'center',
        justifyContent: 'space-around',
      }}>
        {bars.map((amplitude, i) => {
          const barHeight = amplitude * 140;
          return (
            <div key={i} style={{
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', gap: 2,
            }}>
              {/* Top bar */}
              <div style={{
                width: 12, height: barHeight, borderRadius: 2,
                background: `linear-gradient(180deg, ${BRAND.DARK_RED}, ${BRAND.RED})`,
                opacity: 0.9,
                transform: 'scaleY(-1)',
              }} />
              {/* Bottom bar (mirror) */}
              <div style={{
                width: 12, height: barHeight * 0.6, borderRadius: 2,
                background: `linear-gradient(0deg, ${BRAND.DARK_RED}44, ${BRAND.RED}44)`,
                opacity: 0.5,
              }} />
            </div>
          );
        })}
      </div>

      {/* Speaker label */}
      <div style={{
        position: 'absolute', bottom: 80, left: 40,
        background: speakerColor, padding: '10px 20px', borderRadius: 4,
      }}>
        <span style={{
          color: 'white', fontWeight: 700, fontSize: 24,
          fontFamily: 'DejaVu Sans, sans-serif',
        }}>
          {speakerName}
        </span>
      </div>

      {/* BTC ticker bar */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 44, background: BRAND.TICKER_BG,
        overflow: 'hidden', display: 'flex', alignItems: 'center',
      }}>
        <span style={{
          color: BRAND.GOLD, fontSize: 18,
          fontFamily: 'DejaVu Sans Mono, monospace',
          whiteSpace: 'nowrap',
          transform: `translateX(${tickerOffset}px)`,
        }}>
          {tickerText.repeat(10)}
        </span>
      </div>

      {/* Thumbnail PIP (right side) */}
      {thumbnailFile && (
        <div style={{
          position: 'absolute', right: 40, top: 120,
          width: 720, height: 405,
          border: `2px solid rgba(204,0,0,0.8)`,
          borderRadius: 4, overflow: 'hidden',
        }}>
          <img
            src={staticFile(thumbnailFile)}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        </div>
      )}

      <Audio src={staticFile(audioFile)} />
    </AbsoluteFill>
  );
};
