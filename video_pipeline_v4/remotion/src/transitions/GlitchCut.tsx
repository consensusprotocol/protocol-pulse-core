import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { BRAND, GLITCH_CUT_FRAMES } from "../types";
import { ASSETS } from "../assets";

/**
 * GlitchCut — digital glitch transition.
 *
 * Duration: 6 frames (0.2s at 30fps).
 * Fires AT frame 0 of cut (offset=0).
 * Visual: red horizontal scan lines sweep across frame.
 * Audio: whoosh SFX.
 *
 * Dedup logic is handled by PulseCheck.tsx (skip if within 60 frames of last).
 */
export const GlitchCut: React.FC = () => {
  const frame = useCurrentFrame();

  // Sweep progress: 0→1 over 6 frames
  const progress = interpolate(frame, [0, GLITCH_CUT_FRAMES], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Generate scan lines
  const lineCount = 12;
  const lines = Array.from({ length: lineCount }, (_, i) => {
    const y = (i / lineCount) * 1080;
    const lineProgress = interpolate(
      progress,
      [i / lineCount, Math.min((i + 3) / lineCount, 1)],
      [0, 1],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
    return { y, width: lineProgress * 1920, opacity: 1 - progress * 0.5 };
  });

  // Flash effect on first 2 frames
  const flashOpacity = interpolate(frame, [0, 2], [0.3, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent" }}>
      {/* Whoosh SFX */}
      <Audio src={staticFile(ASSETS.WHOOSH)} volume={0.7} />

      {/* Red scan lines */}
      {lines.map((line, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            top: line.y,
            left: 0,
            width: line.width,
            height: 3,
            backgroundColor: BRAND.PRIMARY_RED,
            opacity: line.opacity,
          }}
        />
      ))}

      {/* White flash */}
      <AbsoluteFill
        style={{
          backgroundColor: BRAND.WHITE,
          opacity: flashOpacity,
        }}
      />
    </AbsoluteFill>
  );
};
