
/**
 * Proto-P Behavioral State System v2.0
 * Every state owns ALL parameters. Nothing is hardcoded in the renderer.
 */

export const STATES = {
  IDLE:        "idle",
  LISTENING:   "listening",
  THINKING:    "thinking",
  SPEAKING:    "speaking",
  BROADCAST:   "broadcast",
  INTERRUPTED: "interrupted",
};

export const STATE_CONFIG = {
  idle: {
    // Eye behavior
    blinkIntervalMs:   [3000, 4500],   // [min, max] random range
    blinkDurationMs:   [160, 220],
    gazeMaxOffsetPx:   [8, 4],         // [x, y] max
    saccadeIntervalMs: [2200, 3800],
    gazeFollowsCursor: false,
    // Brow behavior
    browState:         "neutral",      // neutral | attentive | confident | analytical
    browIntensity:     0.0,
    // Mouth
    mouthViseme:       17,             // smile-neutral
    mouthScale:        1.0,
    // Head posture
    headTiltDeg:       0,
    headTiltVariance:  0.6,
    breathingAmp:      1.4,
    breathingSpeed:    0.0018,
    // Glow
    glowIntensity:     0.12,
    glowColor:         [204, 0, 0],    // Protocol Pulse red
    pulseSpeed:        0.0012,
    // Asymmetry (micro-imperfections)
    rightEyeLag:       0.08,           // right eye closes slightly after left
    breathingAsymmetry: 0.15,
  },
  listening: {
    blinkIntervalMs:   [4000, 6000],   // Blinks less — focused
    blinkDurationMs:   [140, 180],
    gazeMaxOffsetPx:   [5, 3],
    saccadeIntervalMs: [1400, 2200],
    gazeFollowsCursor: true,           // Tracks user cursor
    browState:         "attentive",
    browIntensity:     0.4,
    mouthViseme:       0,              // Closed
    mouthScale:        1.0,
    headTiltDeg:       -2.5,           // Slight lean toward user
    headTiltVariance:  0.4,
    breathingAmp:      0.8,
    breathingSpeed:    0.0022,
    glowIntensity:     0.22,
    glowColor:         [0, 180, 255],  // Cyan — engaged
    pulseSpeed:        0.002,
    rightEyeLag:       0.06,
    breathingAsymmetry: 0.08,
  },
  thinking: {
    blinkIntervalMs:   [2200, 3000],   // Deliberate slow blinks
    blinkDurationMs:   [200, 280],
    gazeMaxOffsetPx:   [4, 6],
    saccadeIntervalMs: [3000, 5000],
    gazeFollowsCursor: false,
    browState:         "analytical",
    browIntensity:     0.55,
    mouthViseme:       15,             // Half-open neutral
    mouthScale:        0.85,
    headTiltDeg:       2.8,            // Slight downward — contemplating
    headTiltVariance:  0.3,
    breathingAmp:      0.6,
    breathingSpeed:    0.0015,
    glowIntensity:     0.32,
    glowColor:         [204, 0, 0],
    pulseSpeed:        0.0008,         // Slow compression
    rightEyeLag:       0.12,
    breathingAsymmetry: 0.2,
  },
  speaking: {
    blinkIntervalMs:   [3500, 5000],
    blinkDurationMs:   [130, 170],
    gazeMaxOffsetPx:   [3, 2],         // Minimal drift — focused delivery
    saccadeIntervalMs: [0, 0],         // No saccades during speech
    gazeFollowsCursor: false,
    browState:         "confident",
    browIntensity:     0.3,
    mouthViseme:       null,           // Driven by viseme timeline
    mouthScale:        1.0,
    headTiltDeg:       0,              // Upright — authoritative
    headTiltVariance:  0.8,
    breathingAmp:      1.2,
    breathingSpeed:    0.0025,
    glowIntensity:     0.48,
    glowColor:         [204, 0, 0],
    pulseSpeed:        0.003,          // Fast — matching speech energy
    rightEyeLag:       0.05,
    breathingAsymmetry: 0.1,
  },
  broadcast: {
    blinkIntervalMs:   [3000, 4000],
    blinkDurationMs:   [120, 160],
    gazeMaxOffsetPx:   [2, 1],         // Nearly still — on-air mode
    saccadeIntervalMs: [5000, 8000],
    gazeFollowsCursor: false,
    browState:         "confident",
    browIntensity:     0.6,            // Stronger — authoritative delivery
    mouthViseme:       null,
    mouthScale:        1.05,           // Slightly larger — emphasis
    headTiltDeg:       -1.0,           // Slight chin-up — broadcast posture
    headTiltVariance:  0.3,
    breathingAmp:      0.7,
    breathingSpeed:    0.002,
    glowIntensity:     0.65,           // Maximum presence
    glowColor:         [247, 147, 26], // Bitcoin orange for alerts
    pulseSpeed:        0.004,
    rightEyeLag:       0.04,
    breathingAsymmetry: 0.05,
  },
  interrupted: {
    blinkIntervalMs:   [800, 1200],    // Fast reset blinks
    blinkDurationMs:   [100, 140],
    gazeMaxOffsetPx:   [6, 4],
    saccadeIntervalMs: [600, 1000],
    gazeFollowsCursor: true,
    browState:         "neutral",
    browIntensity:     0.1,
    mouthViseme:       0,
    mouthScale:        0.9,
    headTiltDeg:       1.5,
    headTiltVariance:  1.2,            // Settling — slight overshoot
    breathingAmp:      1.8,
    breathingSpeed:    0.003,
    glowIntensity:     0.08,
    glowColor:         [204, 0, 0],
    pulseSpeed:        0.001,
    rightEyeLag:       0.18,           // More pronounced lag during reset
    breathingAsymmetry: 0.25,
  },
};

export const BROW_PARAMS = {
  neutral:    { lift: 0.0,  furrow: 0.0, asymmetry: 0.0 },
  attentive:  { lift: 0.35, furrow: 0.0, asymmetry: 0.1 },   // Slight inner lift
  confident:  { lift: 0.15, furrow: 0.0, asymmetry: 0.0 },
  analytical: { lift: 0.0,  furrow: 0.5, asymmetry: 0.2 },   // Slight knit
};

// Speech emphasis: maps audio amplitude to parameter scalars
export function getSpeechEmphasis(amplitude) {
  const a = Math.max(0, Math.min(1, amplitude));
  return {
    browLift:      a * 0.55,      // Brows lift on loud syllables
    jawAmplitude:  1.0 + a * 0.4, // Jaw opens slightly wider on emphasis
    glowBoost:     a * 0.3,       // Pulse brightens
    headAccent:    a * 0.8,       // Tiny head forward on peaks
  };
}

// Micro-imperfections — called once per blink cycle
export function getBlinkImperfection() {
  return {
    // Right eye occasionally closes 1–2 frames after left
    rightEyeDelayMs:   Math.random() < 0.3 ? (30 + Math.random() * 50) : 0,
    // Random cluster vs isolated blinks
    nextBlinkOffset:   Math.random() < 0.15 ? (200 + Math.random() * 400) : 0,
    // Gaze occasionally overshoots target
    gazeOvershoots:    Math.random() < 0.2,
    gazeOvershootAmt:  2 + Math.random() * 3,
  };
}
