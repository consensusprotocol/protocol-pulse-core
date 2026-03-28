import React from "react";
import { AbsoluteFill, Audio, Video, staticFile } from "remotion";
import { ASSETS } from "../assets";
import type { Segment } from "../types";

interface OutroSceneProps {
  segment: Segment;
}

/**
 * OutroScene — plays existing outro.mp4 asset exactly.
 * Sign-off narration: "Stay free. Stay sovereign. This is PBX, Protocol Pulse."
 * Audio: outro video audio + PBX sign-off mixed.
 */
export const OutroScene: React.FC<OutroSceneProps> = ({ segment }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {/* Outro video — plays exactly as-is */}
      <Video
        src={staticFile(ASSETS.OUTRO)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />

      {/* PBX sign-off narration mixed over outro */}
      {segment.narration_audio && (
        <Audio src={staticFile(segment.narration_audio)} volume={1} />
      )}
    </AbsoluteFill>
  );
};
