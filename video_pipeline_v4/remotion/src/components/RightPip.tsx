import React from "react";
import { interpolate, useCurrentFrame, Video, Img, staticFile } from "remotion";
import { BRAND, FPS } from "../types";

interface RightPipProps {
  clipPath?: string;
  channelName?: string;
  topic?: string;
}

/**
 * Reusable PIP frame (960x1080 right panel) with 880x495 video frame.
 * - Neutral gray color correction (no red tint)
 * - Ken Burns zoom 1.0→1.05 over duration
 * - Fallback: dark card with channel + topic text
 */
export const RightPip: React.FC<RightPipProps> = ({
  clipPath,
  channelName,
  topic,
}) => {
  const frame = useCurrentFrame();

  // Ken Burns: slow zoom 1.0→1.05 over 5s minimum
  const scale = interpolate(frame, [0, 5 * FPS], [1.0, 1.05], {
    extrapolateRight: "clamp",
  });

  const hasClip = clipPath && clipPath.length > 0;

  return (
    <div
      style={{
        width: 960,
        height: 1080,
        backgroundColor: "#111111",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* PIP frame */}
      <div
        style={{
          width: 880,
          height: 495,
          borderRadius: 8,
          border: "1px solid rgba(255,255,255,0.1)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {hasClip ? (
          <div
            style={{
              width: "100%",
              height: "100%",
              transform: `scale(${scale})`,
              transformOrigin: "center 40%", // Face centering: upper 40%
              filter: "saturate(0) brightness(1.05)", // Neutral gray, no red tint
            }}
          >
            <Video
              src={staticFile(clipPath!)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
              volume={0}
            />
          </div>
        ) : (
          /* Fallback: branded placeholder card */
          <div
            style={{
              width: "100%",
              height: "100%",
              backgroundColor: BRAND.BLACK,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: 40,
            }}
          >
            <div
              style={{
                fontSize: 11,
                letterSpacing: "0.2em",
                color: BRAND.PRIMARY_RED,
                marginBottom: 16,
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              CLIP LOADING...
            </div>
            {channelName && (
              <div
                style={{
                  fontSize: 28,
                  color: BRAND.WHITE,
                  fontFamily: "JetBrains Mono, monospace",
                  fontWeight: "bold",
                  textAlign: "center",
                  marginBottom: 8,
                }}
              >
                {channelName}
              </div>
            )}
            {topic && (
              <div
                style={{
                  fontSize: 18,
                  color: BRAND.TEXT_SECONDARY,
                  textAlign: "center",
                  fontFamily: "JetBrains Mono, monospace",
                }}
              >
                {topic}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
