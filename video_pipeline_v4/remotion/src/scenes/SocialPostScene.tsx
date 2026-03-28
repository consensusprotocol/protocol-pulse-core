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

interface SocialPostSceneProps {
  segment: Segment;
}

/**
 * SocialPostScene — tweet/post overlay with Ken Burns pan.
 *
 * 0.5s delay → card fades in (0.3s) → Ken Burns left→right pan.
 * Post card: 1680x600px, centered.
 */
export const SocialPostScene: React.FC<SocialPostSceneProps> = ({
  segment,
}) => {
  const frame = useCurrentFrame();

  // 0.5s delay (15 frames) before card appears
  const delayFrames = Math.round(0.5 * FPS);
  const fadeIn = interpolate(
    frame - delayFrames,
    [0, Math.round(0.3 * FPS)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Ken Burns: slow left→right pan, 0→40px
  const panX = interpolate(
    frame,
    [0, segment.duration_seconds * FPS],
    [0, 40],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.BLACK }}>
      {/* Narration audio */}
      {segment.narration_audio && (
        <Audio src={staticFile(segment.narration_audio)} volume={1} />
      )}

      {/* Post card */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: `translate(-50%, -50%) translateX(${panX}px)`,
          width: 1680,
          minHeight: 600,
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 16,
          padding: 48,
          opacity: fadeIn,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Avatar + handle row */}
        <div style={{ display: "flex", alignItems: "center", marginBottom: 24 }}>
          {/* Avatar circle */}
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              backgroundColor: "rgba(255,255,255,0.1)",
              marginRight: 16,
              flexShrink: 0,
            }}
          />
          <div>
            <div
              style={{
                fontSize: 18,
                color: BRAND.WHITE,
                fontFamily: "JetBrains Mono, monospace",
                fontWeight: "bold",
              }}
            >
              {segment.post_handle || "@unknown"}
            </div>
            <div
              style={{
                fontSize: 14,
                color: BRAND.TEXT_MUTED,
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              {segment.post_timestamp || ""}
            </div>
          </div>
        </div>

        {/* Post text */}
        <div
          style={{
            fontSize: 52,
            fontFamily: "JetBrains Mono, monospace",
            color: BRAND.WHITE,
            lineHeight: 1.3,
            width: "60%",
            wordWrap: "break-word",
            flex: 1,
          }}
        >
          {segment.post_content || ""}
        </div>

        {/* Engagement metrics */}
        <div
          style={{
            display: "flex",
            gap: 32,
            marginTop: 24,
          }}
        >
          {segment.post_likes != null && (
            <div
              style={{
                fontSize: 14,
                color: BRAND.TEXT_SECONDARY,
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              {segment.post_likes.toLocaleString()} likes
            </div>
          )}
          {segment.post_retweets != null && (
            <div
              style={{
                fontSize: 14,
                color: BRAND.TEXT_SECONDARY,
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              {segment.post_retweets.toLocaleString()} reposts
            </div>
          )}
        </div>
      </div>

      <BrandBorder />
    </AbsoluteFill>
  );
};
