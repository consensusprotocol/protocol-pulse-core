import React from "react";
import { Audio, staticFile } from "remotion";
import { ASSETS } from "../assets";

interface TransitionSFXProps {
  /** Frame offset within parent sequence — fires at frame 0 of cut */
  startFrom?: number;
}

/**
 * SFX audio at frame cut (offset=0).
 * Plays the whoosh sound effect at the transition point.
 */
export const TransitionSFX: React.FC<TransitionSFXProps> = ({
  startFrom = 0,
}) => {
  return (
    <Audio
      src={staticFile(ASSETS.WHOOSH)}
      startFrom={startFrom}
      volume={0.7}
    />
  );
};
