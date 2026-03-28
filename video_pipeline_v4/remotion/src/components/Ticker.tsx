import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { BRAND, FPS, WIDTH } from "../types";

interface TickerProps {
  btcPrice: number;
  fearGreed: number;
  hashrate: number;
}

/**
 * Bottom ticker bar — scrolling data ticker.
 * Height: 40px, background: near-black, red left accent.
 */
export const Ticker: React.FC<TickerProps> = ({
  btcPrice,
  fearGreed,
  hashrate,
}) => {
  const frame = useCurrentFrame();

  const tickerText = [
    `BTC $${btcPrice.toLocaleString("en-US")}`,
    `FEAR & GREED: ${fearGreed}`,
    `HASHRATE: ${hashrate} EH/s`,
    "PROTOCOL PULSE — STAY SOVEREIGN",
  ].join("   •   ");

  // Scroll from right to left
  const scrollX = interpolate(
    frame,
    [0, 20 * FPS],
    [WIDTH, -WIDTH * 2],
    { extrapolateRight: "extend" }
  );

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        width: "100%",
        height: 40,
        backgroundColor: "#0c0c0c",
        borderTop: `1px solid ${BRAND.PRIMARY_RED}`,
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
      }}
    >
      {/* Red accent left edge */}
      <div
        style={{
          width: 4,
          height: "100%",
          backgroundColor: BRAND.PRIMARY_RED,
          position: "absolute",
          left: 0,
          top: 0,
        }}
      />
      <div
        style={{
          whiteSpace: "nowrap",
          fontSize: 14,
          fontFamily: "JetBrains Mono, monospace",
          color: BRAND.TEXT_SECONDARY,
          letterSpacing: "0.1em",
          transform: `translateX(${scrollX}px)`,
        }}
      >
        {tickerText}
      </div>
    </div>
  );
};
