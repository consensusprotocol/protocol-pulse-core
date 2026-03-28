import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { LeftPanel } from "../components/LeftPanel";
import { RightPip } from "../components/RightPip";
import { Ticker } from "../components/Ticker";
import { BrandBorder } from "../components/BrandBorder";
import type { EpisodeSpec, Segment } from "../types";

interface PipSceneProps {
  segment: Segment;
  spec: EpisodeSpec;
}

/**
 * PipScene — 50/50 split layout.
 * Left: dark panel with logo, price, sponsor.
 * Right: partner content PIP with Ken Burns + neutral gray.
 */
export const PipScene: React.FC<PipSceneProps> = ({ segment, spec }) => {
  // A/B rotation: recap uses clip_b, default uses clip_a
  const clipPath = segment.is_recap ? segment.clip_path_b : segment.clip_path;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {/* Narration audio */}
      {segment.narration_audio && (
        <Audio src={staticFile(segment.narration_audio)} volume={1} />
      )}

      {/* Left panel */}
      <div style={{ position: "absolute", left: 0, top: 0 }}>
        <LeftPanel btcPrice={spec.btc_price} date={spec.date} />
      </div>

      {/* Right panel */}
      <div style={{ position: "absolute", left: 960, top: 0 }}>
        <RightPip
          clipPath={clipPath}
          channelName={segment.channel_name}
          topic={segment.topic}
        />
      </div>

      {/* Ticker bar */}
      <Ticker
        btcPrice={spec.btc_price}
        fearGreed={spec.fear_greed.value}
        hashrate={spec.hashrate}
      />

      {/* Brand borders */}
      <BrandBorder />
    </AbsoluteFill>
  );
};
