import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { MetricCard } from "../components/MetricCard";
import { BrandBorder } from "../components/BrandBorder";
import { BRAND, FPS } from "../types";
import { getChartForTopic } from "../assets";
import type { EpisodeSpec, Segment } from "../types";

interface IntelligenceSceneProps {
  segment: Segment;
  spec: EpisodeSpec;
}

/**
 * IntelligenceScene — metric cards (2x3 grid) + chart section.
 * Full 1920x1080, solid #0d0d0d background (no bg_loop).
 */
export const IntelligenceScene: React.FC<IntelligenceSceneProps> = ({
  segment,
  spec,
}) => {
  const frame = useCurrentFrame();

  // Chart Ken Burns: 1.0→1.02 zoom
  const chartScale = interpolate(
    frame,
    [0, Math.max((segment.duration_seconds ?? 15) * FPS, 1)],
    [1.0, 1.02],
    { extrapolateRight: "clamp" }
  );

  const chartSrc = getChartForTopic(segment.chart_type || segment.topic);

  const metrics = [
    {
      label: "BTC PRICE",
      value: `$${spec.btc_price.toLocaleString("en-US")}`,
      valueColor: BRAND.PRIMARY_RED,
    },
    {
      label: "FEAR & GREED",
      value: `${spec.fear_greed.value}`,
      subLabel: spec.fear_greed.label,
      valueColor: BRAND.WHITE,
    },
    {
      label: "HASHRATE",
      value: `${spec.hashrate} EH/s`,
      valueColor: BRAND.GREEN,
    },
    {
      label: "ETF FLOW",
      value: spec.etf_flow || "—",
      valueColor: BRAND.WHITE,
    },
    {
      label: "MEMPOOL FEES",
      value: spec.mempool_fees || "—",
      valueColor: BRAND.WHITE,
    },
    {
      label: "HALVING COUNTDOWN",
      value: spec.halving_countdown || "—",
      valueColor: BRAND.GOLD,
    },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: BRAND.SURFACE_DARK }}>
      {/* Narration audio */}
      {segment.narration_audio && (
        <Audio src={staticFile(segment.narration_audio)} volume={1} />
      )}

      {/* TOP SECTION: header bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: 80,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 48px",
          borderBottom: `2px solid ${BRAND.PRIMARY_RED}`,
        }}
      >
        <div
          style={{
            fontSize: 11,
            letterSpacing: "0.2em",
            color: BRAND.PRIMARY_RED,
            fontFamily: "JetBrains Mono, monospace",
          }}
        >
          TODAY&apos;S INTELLIGENCE
        </div>
        <div
          style={{
            fontSize: 11,
            color: BRAND.TEXT_MUTED,
            fontFamily: "JetBrains Mono, monospace",
          }}
        >
          {spec.date}
        </div>
      </div>

      {/* METRIC CARDS GRID: 2 rows × 3 columns */}
      <div
        style={{
          position: "absolute",
          top: 100,
          left: 0,
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
        }}
      >
        {/* Row 1 */}
        <div style={{ display: "flex", gap: 24 }}>
          {metrics.slice(0, 3).map((m, i) => (
            <MetricCard
              key={m.label}
              label={m.label}
              value={m.value}
              subLabel={m.subLabel}
              valueColor={m.valueColor}
              index={i}
            />
          ))}
        </div>
        {/* Row 2 */}
        <div style={{ display: "flex", gap: 24 }}>
          {metrics.slice(3, 6).map((m, i) => (
            <MetricCard
              key={m.label}
              label={m.label}
              value={m.value}
              subLabel={m.subLabel}
              valueColor={m.valueColor}
              index={i + 3}
            />
          ))}
        </div>
      </div>

      {/* CHART SECTION */}
      <div
        style={{
          position: "absolute",
          top: 420,
          left: 48,
          right: 48,
          bottom: 60,
          overflow: "hidden",
          borderRadius: 8,
        }}
      >
        <Img
          src={staticFile(chartSrc)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            transform: `scale(${chartScale})`,
            transformOrigin: "center center",
          }}
        />
      </div>

      <BrandBorder />
    </AbsoluteFill>
  );
};
