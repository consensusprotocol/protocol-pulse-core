import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { BRAND, FPS } from "../types";
import { ASSETS } from "../assets";

interface ColdOpenProps {
  btcPrice: number;
  shockDataLabel: string;
  shockDataValue: string;
  narrationAudio?: string;
}

/**
 * ColdOpen — 4 seconds (120 frames at 30fps).
 *
 * Frame 0-30:  BTC price slams in from left + red line sweep
 * Frame 30-90: Shock data fades in below price + logo bottom-right
 * Frame 90-120: Hold — hard cut via GlitchCut at frame 120
 */
export const ColdOpen: React.FC<ColdOpenProps> = ({
  btcPrice,
  shockDataLabel,
  shockDataValue,
  narrationAudio,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const formattedPrice = `$${btcPrice.toLocaleString("en-US")}`;

  // Phase 1 (0-30): Price slams in from left via spring
  const priceX = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 120 },
    from: -1920,
    to: 0,
  });

  // Red horizontal line sweeps left→right
  const lineWidth = interpolate(frame, [0, FPS], [0, 1920], {
    extrapolateRight: "clamp",
  });

  // Phase 2 (30-90): Shock data fades in
  const shockOpacity = interpolate(frame, [30, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Logo appears bottom-right
  const logoOpacity = interpolate(frame, [35, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.BLACK }}>
      {/* Narration audio */}
      {narrationAudio && (
        <Audio src={staticFile(narrationAudio)} volume={1} />
      )}

      {/* BTC Price — slams in from left */}
      <div
        style={{
          position: "absolute",
          top: 340,
          left: 0,
          width: "100%",
          display: "flex",
          justifyContent: "center",
          transform: `translateX(${priceX - 960 + 960}px)`,
        }}
      >
        <div
          style={{
            fontSize: 96,
            fontFamily: "JetBrains Mono, monospace",
            fontWeight: "bold",
            color: BRAND.WHITE,
          }}
        >
          {formattedPrice}
        </div>
      </div>

      {/* Red horizontal line sweep */}
      <div
        style={{
          position: "absolute",
          top: 460,
          left: 0,
          width: lineWidth,
          height: 3,
          backgroundColor: BRAND.PRIMARY_RED,
        }}
      />

      {/* Shock data — fades in after 1s */}
      <div
        style={{
          position: "absolute",
          top: 490,
          left: 0,
          width: "100%",
          textAlign: "center",
          opacity: shockOpacity,
        }}
      >
        <div
          style={{
            fontSize: 48,
            fontFamily: "JetBrains Mono, monospace",
            color: BRAND.PRIMARY_RED,
            fontWeight: "bold",
          }}
        >
          {shockDataLabel}: {shockDataValue}
        </div>
      </div>

      {/* Protocol Pulse logo — bottom-right, subtle */}
      <Img
        src={staticFile(ASSETS.LOGO)}
        style={{
          position: "absolute",
          bottom: 40,
          right: 40,
          width: 80,
          height: 80,
          opacity: logoOpacity,
          objectFit: "contain",
        }}
      />
    </AbsoluteFill>
  );
};
