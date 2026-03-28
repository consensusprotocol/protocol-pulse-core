import React from "react";
import { interpolate, useCurrentFrame, Img, staticFile } from "remotion";
import { BRAND, FPS, getSponsor } from "../types";
import { ASSETS } from "../assets";

interface LeftPanelProps {
  btcPrice: number;
  date: string;
}

/**
 * Reusable dark left panel (960x1080) — logo, BTC price, sponsor lower-third.
 * Background: solid #0d0d0d (NOT bg_loop.mp4).
 */
export const LeftPanel: React.FC<LeftPanelProps> = ({ btcPrice, date }) => {
  const frame = useCurrentFrame();
  const sponsor = getSponsor(date);

  // Subtle 2s pulse animation on logo (opacity 1→0.7→1)
  const pulsePhase = (frame / FPS) % 2;
  const logoOpacity = interpolate(
    pulsePhase,
    [0, 1, 2],
    [1, 0.7, 1],
    { extrapolateRight: "clamp" }
  );

  const formattedPrice = `$${btcPrice.toLocaleString("en-US")}`;

  return (
    <div
      style={{
        width: 960,
        height: 1080,
        backgroundColor: BRAND.SURFACE_DARK,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
      }}
    >
      {/* Top red border */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: 2,
          backgroundColor: BRAND.PRIMARY_RED,
        }}
      />

      {/* Logo with pulse */}
      <Img
        src={staticFile(ASSETS.LOGO)}
        style={{
          width: 120,
          height: 120,
          opacity: logoOpacity,
          objectFit: "contain",
        }}
      />

      {/* Red horizontal accent line */}
      <div
        style={{
          width: "100%",
          height: 2,
          backgroundColor: BRAND.PRIMARY_RED,
          opacity: 0.4,
          marginTop: 24,
          marginBottom: 24,
        }}
      />

      {/* BTC Price */}
      <div
        style={{
          fontSize: 64,
          fontFamily: "JetBrains Mono, monospace",
          fontWeight: "bold",
          color: BRAND.WHITE,
        }}
      >
        {formattedPrice}
      </div>

      {/* LIVE INTELLIGENCE label */}
      <div
        style={{
          fontSize: 11,
          letterSpacing: "0.2em",
          color: BRAND.TEXT_FAINT,
          marginTop: 12,
          textTransform: "uppercase",
          fontFamily: "JetBrains Mono, monospace",
        }}
      >
        LIVE INTELLIGENCE
      </div>

      {/* Sponsor lower-third */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: 0,
          width: "100%",
          textAlign: "center",
          fontSize: 13,
          color: BRAND.TEXT_MUTED,
          fontFamily: "JetBrains Mono, monospace",
          letterSpacing: "0.05em",
        }}
      >
        {sponsor.text}
      </div>

      {/* Bottom red border */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "100%",
          height: 2,
          backgroundColor: BRAND.PRIMARY_RED,
        }}
      />
    </div>
  );
};
