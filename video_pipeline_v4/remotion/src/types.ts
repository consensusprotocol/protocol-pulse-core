/**
 * Protocol Pulse V4 — Episode specification types.
 * Matches the JSON contract from daily_producer.py / assembler.py.
 */

export interface EpisodeSpec {
  date: string;
  btc_price: number;
  fear_greed: FearGreed;
  hashrate: number;
  etf_flow?: string;
  mempool_fees?: string;
  halving_countdown?: string;
  episode_title?: string;
  segments: Segment[];
}

export interface FearGreed {
  value: number;
  label: string;
}

export type SegmentType =
  | "cold_open"
  | "pip"
  | "intelligence"
  | "social"
  | "spaces"
  | "narration"
  | "outro";

export interface Segment {
  type: SegmentType;
  duration_seconds: number;
  narration_audio?: string;
  clip_path?: string;
  clip_path_b?: string;
  topic?: string;
  narration_text?: string;
  post_content?: string;
  post_handle?: string;
  post_avatar?: string;
  post_timestamp?: string;
  post_likes?: number;
  post_retweets?: number;
  chart_type?: string;
  spaces_audio?: string;
  spaces_transcript?: string;
  spaces_speaker?: string;
  spaces_followers?: number;
  channel_name?: string;
  is_recap?: boolean;
  bullet_points?: string[];
}

export interface PulseCheckProps extends Record<string, unknown> {
  specPath?: string;
}

/** Brand color constants — PIPELINE_LAWS Section 10 */
export const BRAND = {
  PRIMARY_RED: "#CC0000",
  DARK_RED: "#880000",
  LIGHT_RED: "#FF4444",
  BLACK: "#0A0A0A",
  SURFACE: "#141414",
  SURFACE_DARK: "#0D0D0D",
  SURFACE_DARKER: "#080D12",
  WHITE: "#FFFFFF",
  WARM_WHITE: "#F4F5F8",
  BORDER: "#1F1F1F",
  TEXT_SECONDARY: "#888888",
  TEXT_MUTED: "rgba(255,255,255,0.4)",
  TEXT_FAINT: "rgba(255,255,255,0.3)",
  GOLD: "#F8C15C",
  GREEN: "#6EE7B7",
  CARD_BG: "rgba(220,38,38,0.06)",
  CARD_BORDER: "rgba(220,38,38,0.2)",
} as const;

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

/** Transition durations in frames */
export const GLITCH_CUT_FRAMES = 6;
export const FADE_TO_BLACK_FRAMES = 15;
export const GLITCH_DEDUP_FRAMES = 60;

/** Sponsor rotation */
export const SPONSORS = [
  { name: "Curated Mining", text: "curatedmining.com — white-glove Bitcoin mining" },
  { name: "Meanwhile", text: "meanwhile.com code KKM73K — Bitcoin life insurance" },
  { name: "River", text: "river.com — buy Bitcoin, no minimums" },
] as const;

export function getSponsor(dateStr: string): (typeof SPONSORS)[number] {
  const d = new Date(dateStr);
  const start = new Date(d.getFullYear(), 0, 0);
  const diff = d.getTime() - start.getTime();
  const dayOfYear = Math.floor(diff / (1000 * 60 * 60 * 24));
  return SPONSORS[dayOfYear % 3];
}
