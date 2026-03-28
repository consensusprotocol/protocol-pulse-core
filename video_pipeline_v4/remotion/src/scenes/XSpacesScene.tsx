import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { BrandBorder } from "../components/BrandBorder";
import { BRAND, FPS } from "../types";
import type { Segment } from "../types";

interface XSpacesSceneProps {
  segment: Segment;
}

/**
 * XSpacesScene — X Spaces live signal.
 * Background: #080d12.
 * Header bar + animated waveform bars + transcript area.
 * Audio plays to completion (up to 45s).
 */
export const XSpacesScene: React.FC<XSpacesSceneProps> = ({ segment }) => {
  const frame = useCurrentFrame();

  // Pulsing red dot animation
  const pulseOpacity = interpolate(
    (frame / FPS) % 1,
    [0, 0.5, 1],
    [1, 0.3, 1]
  );

  // Generate pseudo-random waveform bar heights based on frame
  const barCount = 40;
  const bars = Array.from({ length: barCount }, (_, i) => {
    const seed = (frame * 7 + i * 13) % 100;
    const height = 10 + (seed / 100) * 50;
    return height;
  });

  // Transcript scroll (smooth)
  const transcriptLength = (segment.spaces_transcript || "").length;
  const scrollY = transcriptLength > 500
    ? interpolate(
        frame,
        [0, Math.max((segment.duration_seconds ?? 15) * FPS, 1)],
        [0, -(transcriptLength / 3)],
        { extrapolateRight: "clamp" }
      )
    : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.SURFACE_DARKER }}>
      {/* Narration audio (PBX intro) */}
      {segment.narration_audio && (
        <Audio src={staticFile(segment.narration_audio)} volume={1} playbackRate={0.75} />
      )}

      {/* Spaces audio (plays to completion) */}
      {segment.spaces_audio && (
        <Audio src={staticFile(segment.spaces_audio)} volume={1} />
      )}

      {/* HEADER BAR */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: 60,
          display: "flex",
          alignItems: "center",
          padding: "0 48px",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Red pulsing dot */}
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: BRAND.PRIMARY_RED,
              opacity: pulseOpacity,
            }}
          />
          <div
            style={{
              fontSize: 11,
              letterSpacing: "0.2em",
              color: BRAND.PRIMARY_RED,
              fontFamily: "JetBrains Mono, monospace",
            }}
          >
            SIGNAL ACTIVE — X SPACES LIVE
          </div>
        </div>

        {/* Speaker info */}
        <div
          style={{
            fontSize: 13,
            color: BRAND.TEXT_MUTED,
            fontFamily: "JetBrains Mono, monospace",
          }}
        >
          {segment.spaces_speaker || "Live Speaker"}
          {segment.spaces_followers
            ? ` • ${segment.spaces_followers.toLocaleString()} followers`
            : ""}
        </div>
      </div>

      {/* WAVEFORM BARS */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 48,
          right: 48,
          height: 60,
          display: "flex",
          alignItems: "flex-end",
          gap: 3,
        }}
      >
        {bars.map((h, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: h,
              backgroundColor: BRAND.PRIMARY_RED,
              borderRadius: 2,
              opacity: 0.8,
            }}
          />
        ))}
      </div>

      {/* TRANSCRIPT AREA */}
      <div
        style={{
          position: "absolute",
          top: 140,
          left: 48,
          right: 48,
          bottom: 60,
          background: "rgba(255,255,255,0.02)",
          borderRadius: 8,
          padding: 32,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            transform: `translateY(${scrollY}px)`,
            fontSize: 18,
            color: "rgba(255,255,255,0.7)",
            fontFamily: "JetBrains Mono, monospace",
            lineHeight: 1.8,
            whiteSpace: "pre-wrap",
          }}
        >
          {segment.spaces_transcript || "AWAITING LIVE SIGNAL"}
        </div>
      </div>

      <BrandBorder />
    </AbsoluteFill>
  );
};
