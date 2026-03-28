import React from "react";
import { AbsoluteFill } from "remotion";
import { BRAND } from "../types";

/**
 * Red border lines (brand) — 2px at all edges per PIPELINE_LAWS.
 */
export const BrandBorder: React.FC<{ opacity?: number }> = ({
  opacity = 0.75,
}) => {
  const style: React.CSSProperties = {
    position: "absolute",
    backgroundColor: BRAND.PRIMARY_RED,
    opacity,
  };

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* Top */}
      <div style={{ ...style, top: 0, left: 0, width: "100%", height: 2 }} />
      {/* Bottom */}
      <div
        style={{ ...style, bottom: 0, left: 0, width: "100%", height: 2 }}
      />
      {/* Left */}
      <div style={{ ...style, top: 0, left: 0, width: 2, height: "100%" }} />
      {/* Right */}
      <div style={{ ...style, top: 0, right: 0, width: 2, height: "100%" }} />
    </AbsoluteFill>
  );
};
