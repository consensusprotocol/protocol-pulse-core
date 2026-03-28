import React from "react";
import {
  Composition,
  Sequence,
  staticFile,
  getInputProps,
} from "remotion";
import {
  FPS,
  WIDTH,
  HEIGHT,
  GLITCH_CUT_FRAMES,
  GLITCH_DEDUP_FRAMES,
} from "../types";
import type { EpisodeSpec, PulseCheckProps, Segment } from "../types";
import { ColdOpen } from "../scenes/ColdOpen";
import { PipScene } from "../scenes/PipScene";
import { IntelligenceScene } from "../scenes/IntelligenceScene";
import { SocialPostScene } from "../scenes/SocialPostScene";
import { XSpacesScene } from "../scenes/XSpacesScene";
import { NarrationScene } from "../scenes/NarrationScene";
import { OutroScene } from "../scenes/OutroScene";
import { GlitchCut } from "../transitions/GlitchCut";

/**
 * PulseCheck — master composition that assembles all scenes.
 *
 * Reads episode_spec.json, builds timeline:
 * 1. ColdOpen (4s)
 * 2. Segments from spec with GlitchCut between each
 * 3. Outro (last)
 */

interface TimelineEntry {
  type: "scene" | "transition";
  startFrame: number;
  durationFrames: number;
  segment?: Segment;
}

function buildTimeline(spec: EpisodeSpec): {
  entries: TimelineEntry[];
  totalFrames: number;
} {
  const entries: TimelineEntry[] = [];
  let currentFrame = 0;
  let lastTransitionFrame = -GLITCH_DEDUP_FRAMES - 1; // Allow first transition

  for (let i = 0; i < spec.segments.length; i++) {
    const seg = spec.segments[i];
    const durationFrames = Math.round((seg.duration_seconds ?? 15) * FPS);

    // Insert GlitchCut between segments (dedup: skip if within 60 frames)
    if (i > 0 && currentFrame - lastTransitionFrame >= GLITCH_DEDUP_FRAMES) {
      entries.push({
        type: "transition",
        startFrame: currentFrame,
        durationFrames: GLITCH_CUT_FRAMES,
      });
      lastTransitionFrame = currentFrame;
      currentFrame += GLITCH_CUT_FRAMES;
    }

    entries.push({
      type: "scene",
      startFrame: currentFrame,
      durationFrames,
      segment: seg,
    });
    currentFrame += durationFrames;
  }

  return { entries, totalFrames: currentFrame };
}

const PulseCheckVideo: React.FC<{ spec: EpisodeSpec }> = ({ spec }) => {
  const { entries } = buildTimeline(spec);

  return (
    <>
      {entries.map((entry, i) => {
        if (entry.type === "transition") {
          return (
            <Sequence
              key={`transition-${i}`}
              from={entry.startFrame}
              durationInFrames={entry.durationFrames}
              name="GlitchCut"
            >
              <GlitchCut />
            </Sequence>
          );
        }

        const seg = entry.segment!;
        return (
          <Sequence
            key={`scene-${i}`}
            from={entry.startFrame}
            durationInFrames={entry.durationFrames}
            name={`${seg.type}-${i}`}
          >
            {renderScene(seg, spec)}
          </Sequence>
        );
      })}
    </>
  );
};

function renderScene(seg: Segment, spec: EpisodeSpec): React.ReactNode {
  switch (seg.type) {
    case "cold_open":
      return (
        <ColdOpen
          btcPrice={spec.btc_price}
          shockDataLabel={
            spec.fear_greed.value < 25
              ? "FEAR & GREED"
              : "BITCOIN"
          }
          shockDataValue={
            spec.fear_greed.value < 25
              ? `${spec.fear_greed.value} — ${spec.fear_greed.label.toUpperCase()}`
              : `$${spec.btc_price.toLocaleString("en-US")}`
          }
          narrationAudio={seg.narration_audio}
        />
      );
    case "pip":
      return <PipScene segment={seg} spec={spec} />;
    case "intelligence":
      return <IntelligenceScene segment={seg} spec={spec} />;
    case "social":
      return <SocialPostScene segment={seg} />;
    case "spaces":
      return <XSpacesScene segment={seg} />;
    case "narration":
      return <NarrationScene segment={seg} spec={spec} />;
    case "outro":
      return <OutroScene segment={seg} />;
    default:
      return <NarrationScene segment={seg} spec={spec} />;
  }
}

// Default test spec for preview/build
const DEFAULT_SPEC: EpisodeSpec = {
  date: "2026-03-28",
  btc_price: 87432,
  fear_greed: { value: 45, label: "Fear" },
  hashrate: 892,
  segments: [
    { type: "cold_open", duration_seconds: 4 },
    { type: "intelligence", duration_seconds: 30, chart_type: "price" },
    { type: "narration", duration_seconds: 15, topic: "intro" },
    { type: "outro", duration_seconds: 10 },
  ],
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="PulseCheck"
        component={PulseCheckWrapper}
        durationInFrames={30 * 60 * 12} // 12 min max
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{ specPath: "/episode_spec.json" } satisfies PulseCheckProps}
      />
    </>
  );
};

const PulseCheckWrapper: React.FC<PulseCheckProps> = () => {
  // In render mode, the spec is loaded via inputProps.
  // In preview mode, use the default spec.
  const inputProps = getInputProps();
  let spec: EpisodeSpec;

  try {
    const specData = inputProps as Record<string, unknown>;
    if (specData?.spec && typeof specData.spec === "object") {
      spec = specData.spec as EpisodeSpec;
    } else {
      spec = DEFAULT_SPEC;
    }
  } catch {
    spec = DEFAULT_SPEC;
  }

  return <PulseCheckVideo spec={spec} />;
};
