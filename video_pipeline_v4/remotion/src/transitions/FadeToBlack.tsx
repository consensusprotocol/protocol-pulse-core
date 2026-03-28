import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FADE_TO_BLACK_FRAMES } from "../types";

/**
 * FadeToBlack — for cold open entry only.
 * Duration: 15 frames (0.5s).
 */
export const FadeToBlack: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, FADE_TO_BLACK_FRAMES], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000000",
        opacity,
      }}
    />
  );
};
