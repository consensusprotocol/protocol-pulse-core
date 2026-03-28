import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { BRAND, FPS } from "../types";

interface MetricCardProps {
  label: string;
  value: string;
  subLabel?: string;
  valueColor?: string;
  index: number;
}

/**
 * Single metric card — stagger animation: slide up 20px + fade in.
 * Card: 580x140px, rgba(220,38,38,0.06) bg, 12px radius.
 */
export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subLabel,
  valueColor = BRAND.WHITE,
  index,
}) => {
  const frame = useCurrentFrame();
  const staggerDelay = index * (0.1 * FPS); // 0.1s stagger per card

  const opacity = interpolate(frame - staggerDelay, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const translateY = interpolate(frame - staggerDelay, [0, 10], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: 580,
        height: 140,
        background: BRAND.CARD_BG,
        border: `1px solid ${BRAND.CARD_BORDER}`,
        borderRadius: 12,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
    >
      <div
        style={{
          fontSize: 11,
          letterSpacing: "0.15em",
          color: BRAND.TEXT_MUTED,
          textTransform: "uppercase",
          fontFamily: "JetBrains Mono, monospace",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 42,
          fontFamily: "JetBrains Mono, monospace",
          fontWeight: "bold",
          color: valueColor,
          marginTop: 4,
        }}
      >
        {value}
      </div>
      {subLabel && (
        <div
          style={{
            fontSize: 13,
            color: BRAND.TEXT_MUTED,
            marginTop: 2,
          }}
        >
          {subLabel}
        </div>
      )}
    </div>
  );
};
