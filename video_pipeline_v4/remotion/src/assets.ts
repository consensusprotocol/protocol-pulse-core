/**
 * Asset path constants — resolved relative to Remotion public/ directory.
 * public/assets is a symlink to video_pipeline_v3/assets.
 */

export const ASSETS = {
  // Logo
  LOGO: "/assets/logo_protocol_pulse.png",
  WATERMARK: "/assets/logo/watermark.png",

  // Videos
  INTRO: "/assets/intro.mp4",
  OUTRO: "/assets/outro_branded.mp4",
  OUTRO_NEW: "/assets/outro_branded_new.mp4",
  BG_LOOP: "/assets/bg_loop.mp4",

  // Transitions
  GLITCH_TRANSITION: "/assets/transitions/glitch_transition_waud.mp4",
  DIGITAL_TRANSITION: "/assets/transitions/digital_transition_1080p.mov",

  // SFX
  WHOOSH: "/assets/sfx/custom_whoosh.wav",
  CARD_SWOOSH: "/assets/sfx/card_swoosh.wav",
  DATA_BLIP: "/assets/sfx/data_blip.wav",

  // Charts (captured fresh each run, placed in public/data/)
  CHART_PRICE: "/assets/charts/btc_price.png",
  CHART_HASHRATE: "/assets/charts/hashrate.png",
  CHART_DIFFICULTY: "/assets/charts/difficulty.png",
  CHART_LTH: "/assets/charts/lth_supply.png",
  CHART_ETF: "/assets/charts/etf_flow.png",

  // Fonts (loaded via @font-face in Remotion)
  FONT_JETBRAINS: "/assets/fonts/JetBrainsMono-Bold.ttf",
  FONT_INTER: "/assets/fonts/Inter-Regular.ttf",
  FONT_INTER_BOLD: "/assets/fonts/Inter-Bold.ttf",

  // B-roll fallback directory
  BROLL_DIR: "/assets/broll/",
  // Narration background music — fixed track, plays on all narration segments
  NARRATION_BG_MUSIC: "/assets/music/contemplative_01.mp3",
} as const;

/**
 * Chart routing — strict keyword→chart mapping per PIPELINE_LAWS Section 19.
 */
export function getChartForTopic(topic?: string): string {
  if (!topic) return ASSETS.CHART_PRICE;
  const t = topic.toLowerCase();
  if (t.includes("hashrate") || t.includes("mining")) return ASSETS.CHART_HASHRATE;
  if (t.includes("difficulty")) return ASSETS.CHART_DIFFICULTY;
  if (t.includes("long-term holder") || t.includes("lth")) return ASSETS.CHART_LTH;
  if (t.includes("etf")) return ASSETS.CHART_ETF;
  return ASSETS.CHART_PRICE;
}
