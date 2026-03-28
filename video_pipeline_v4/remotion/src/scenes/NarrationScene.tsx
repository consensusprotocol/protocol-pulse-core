import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";
import { BrandBorder } from "../components/BrandBorder";
import { BRAND, FPS } from "../types";
import { ASSETS, getChartForTopic } from "../assets";
import type { EpisodeSpec, Segment } from "../types";

interface NarrationSceneProps {
  segment: Segment;
  spec: EpisodeSpec;
}

/**
 * NarrationScene — PBX full-frame narration.
 * Background: solid #0a0a0a. No bg_loop.
 * Content varies by narration context.
 */
export const NarrationScene: React.FC<NarrationSceneProps> = ({
  segment,
  spec,
}) => {
  const frame = useCurrentFrame();
  const isIntro = segment.type === "narration" && segment.topic === "intro";
  const isRecap = segment.type === "narration" && segment.is_recap;

  // Chart Ken Burns
  const chartScale = interpolate(
    frame,
    [0, segment.duration_seconds * FPS],
    [1.0, 1.02],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {/* Narration audio */}
      {segment.narration_audio && (
        <Audio src={staticFile(segment.narration_audio)} volume={1} />
      )}

      {/* Logo centered */}
      <Img
        src={staticFile(ASSETS.LOGO)}
        style={{
          position: "absolute",
          top: 60,
          left: "50%",
          transform: "translateX(-50%)",
          width: 120,
          height: 120,
          objectFit: "contain",
          opacity: 0.8,
        }}
      />

      {isIntro ? (
        /* Intro: BTC price prominently */
        <div
          style={{
            position: "absolute",
            top: 300,
            left: 0,
            width: "100%",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 11,
              letterSpacing: "0.2em",
              color: BRAND.TEXT_FAINT,
              fontFamily: "JetBrains Mono, monospace",
              marginBottom: 16,
            }}
          >
            BITCOIN PRICE
          </div>
          <div
            style={{
              fontSize: 96,
              fontFamily: "JetBrains Mono, monospace",
              fontWeight: "bold",
              color: BRAND.WHITE,
            }}
          >
            ${spec.btc_price.toLocaleString("en-US")}
          </div>
          <div
            style={{
              fontSize: 24,
              color: BRAND.TEXT_SECONDARY,
              marginTop: 16,
              fontFamily: "JetBrains Mono, monospace",
            }}
          >
            {spec.date}
          </div>
        </div>
      ) : isRecap ? (
        /* Recap: bullet points summary */
        <div
          style={{
            position: "absolute",
            top: 240,
            left: 200,
            right: 200,
          }}
        >
          <div
            style={{
              fontSize: 11,
              letterSpacing: "0.2em",
              color: BRAND.PRIMARY_RED,
              fontFamily: "JetBrains Mono, monospace",
              marginBottom: 32,
            }}
          >
            EPISODE RECAP
          </div>
          {(segment.bullet_points || []).map((point, i) => {
            const fadeIn = interpolate(
              frame - i * 15,
              [0, 10],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            return (
              <div
                key={i}
                style={{
                  fontSize: 28,
                  color: BRAND.WARM_WHITE,
                  fontFamily: "JetBrains Mono, monospace",
                  marginBottom: 24,
                  opacity: fadeIn,
                  paddingLeft: 24,
                  borderLeft: `3px solid ${BRAND.PRIMARY_RED}`,
                }}
              >
                {point}
              </div>
            );
          })}
        </div>
      ) : (
        /* Standard: chart or topic graphic */
        <div
          style={{
            position: "absolute",
            top: 220,
            left: 120,
            right: 120,
            bottom: 100,
            overflow: "hidden",
            borderRadius: 8,
          }}
        >
          <Img
            src={staticFile(getChartForTopic(segment.topic))}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              transform: `scale(${chartScale})`,
              transformOrigin: "center center",
            }}
          />
        </div>
      )}

      {/* Narration text overlay — bottom */}
      {segment.narration_text && (
        <div
          style={{
            position: "absolute",
            bottom: 60,
            left: 120,
            right: 120,
            textAlign: "center",
            fontSize: 18,
            color: BRAND.TEXT_SECONDARY,
            fontFamily: "JetBrains Mono, monospace",
            lineHeight: 1.6,
          }}
        >
          {segment.narration_text.length > 120
            ? segment.narration_text.slice(0, 120) + "..."
            : segment.narration_text}
        </div>
      )}

      <BrandBorder />
    </AbsoluteFill>
  );
};
