
/**
 * OracleTuningPanel — Creative Director Mode
 * Toggle with Ctrl+Shift+T (or Cmd+Shift+T)
 * Live-updates behavior params without redeploying.
 * Ships disabled in production (TUNING_MODE=false)
 */

export const TUNING_MODE = (
  typeof window !== "undefined" &&
  (window.location.search.includes("tune=1") ||
   window.location.hostname === "localhost")
);

// Central live-mutable config — renderers read from this
export const LIVE_CONFIG = {
  // ── Blink ─────────────────────────────────────────────────────
  blinkAsymmetryMax:      50,    // ms, max right-eye lag
  blinkAsymmetryChance:   0.30,  // 0–1 probability per blink
  blinkClusterChance:     0.15,  // probability of cluster follow-up
  blinkClusterOffsetMs:   300,   // ms before cluster blink fires

  // ── Gaze ──────────────────────────────────────────────────────
  gazeOvershootChance:    0.20,  // 0–1
  gazeOvershootAmtPx:     3.5,   // pixels
  saccadeReturnSpeed:     0.06,  // lerp factor back to target

  // ── Brow ──────────────────────────────────────────────────────
  browIntensityScale:     1.0,   // global multiplier (0.5 = subtler)
  browSpeechLiftMax:      0.55,  // max lift on loud syllable
  browAsymmetry:          0.15,  // inner vs outer lift difference

  // ── Jaw / mouth (speaking) ────────────────────────────────────
  jawAmplitudeBase:       1.0,   // base jaw open scalar
  jawEmphasisMax:         0.40,  // added on peak amplitude
  mouthBlendSpeed:        0.22,  // viseme interpolation factor

  // ── Glow ──────────────────────────────────────────────────────
  glowAmplitudeBoost:     0.30,  // max added glow on speech peak
  glowPulseRestrained:    true,  // if true, cap glow to avoid gamey feel

  // ── Head motion ───────────────────────────────────────────────
  headBobAmp:             0.8,   // speaking head accent amplitude
  headBreathingAmp:       1.4,   // idle breathing amplitude
  headPerlinSpeed:        0.003, // motion noise speed

  // ── Broadcast ─────────────────────────────────────────────────
  broadcastPostureTight:  true,  // tighter posture vs louder animation
  broadcastGlowCap:       0.65,  // prevent over-brightness
  broadcastBrowConfidence:0.60,  // stronger brow on broadcast

  // ── Activation sequence ───────────────────────────────────────
  activationDurationMs:   1200,  // total sequence length
  chromaticSplitMaxPx:    4,     // restrain chromatic aberration
  scanlineCyanOpacity:    0.85,  // scanline stripe opacity
  hologramEdgeGlow:       0.35,  // edge glow intensity on resolve

  // ── Voice orb ─────────────────────────────────────────────────
  orbWaveformMaxAmp:      0.10,  // radial waveform max radius fraction
  orbHaloPulseRestrained: true,  // prevent over-animation on halo
  orbInnerPulseSpeed:     2.2,   // speaking core pulse speed

  // ── Hair shimmer ──────────────────────────────────────────────
  hairShimmerVisible:     false, // optical shimmer on red streak
  hairShimmerIntensity:   0.12,  // very subtle by default
  hairEdgeGlowOnly:       true,  // edge glow vs physical wave
};

// ── Panel UI ──────────────────────────────────────────────────────────────

const SECTIONS = [
  {
    label: "BLINK", color: "#4fc3f7", params: [
      ["blinkAsymmetryMax",    0, 150,  1, "Right-eye lag max (ms)"],
      ["blinkAsymmetryChance", 0, 1, 0.01, "Asymmetry probability"],
      ["blinkClusterChance",   0, 1, 0.01, "Cluster blink chance"],
    ],
  },
  {
    label: "GAZE", color: "#80cbc4", params: [
      ["gazeOvershootChance",  0, 1,  0.01, "Overshoot probability"],
      ["gazeOvershootAmtPx",   0, 10, 0.5,  "Overshoot amount (px)"],
      ["saccadeReturnSpeed",   0.01, 0.2, 0.005, "Return lerp speed"],
    ],
  },
  {
    label: "BROW", color: "#ce93d8", params: [
      ["browIntensityScale",   0, 2,   0.05, "Global intensity scale"],
      ["browSpeechLiftMax",    0, 1,   0.05, "Max speech lift"],
      ["browAsymmetry",        0, 0.5, 0.02, "Inner/outer asymmetry"],
    ],
  },
  {
    label: "JAW/MOUTH", color: "#ffcc80", params: [
      ["jawAmplitudeBase",     0.5, 1.5, 0.05, "Base jaw scalar"],
      ["jawEmphasisMax",       0,   0.8, 0.05, "Emphasis jaw boost"],
      ["mouthBlendSpeed",      0.05, 0.5, 0.01, "Viseme blend speed"],
    ],
  },
  {
    label: "GLOW", color: "#ef9a9a", params: [
      ["glowAmplitudeBoost",   0,  0.6, 0.02, "Speech glow boost"],
    ],
  },
  {
    label: "HEAD", color: "#a5d6a7", params: [
      ["headBobAmp",           0,  2,   0.1,  "Speaking bob amplitude"],
      ["headBreathingAmp",     0,  3,   0.1,  "Idle breathing amplitude"],
      ["headPerlinSpeed",      0.001, 0.01, 0.0005, "Motion noise speed"],
    ],
  },
  {
    label: "BROADCAST", color: "#f7931a", params: [
      ["broadcastBrowConfidence", 0, 1, 0.05, "Brow confidence level"],
      ["broadcastGlowCap",     0.2, 1.0, 0.05, "Max glow (prevent loud)"],
    ],
  },
  {
    label: "HAIR SHIMMER", color: "#ff8a80", params: [
      ["hairShimmerIntensity", 0, 0.4, 0.01, "Shimmer intensity"],
    ],
  },
];

let _panelEl = null;

export function initTuningPanel() {
  if (!TUNING_MODE) return;
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "T") {
      e.preventDefault();
      togglePanel();
    }
  });
  console.log("[OracleTuning] Ready — Ctrl+Shift+T to open");
}

function togglePanel() {
  if (_panelEl) { _panelEl.remove(); _panelEl = null; return; }

  const panel = document.createElement("div");
  panel.id = "oracle-tuning-panel";
  panel.style.cssText = `
    position:fixed; top:0; right:0; width:320px; height:100vh;
    background:rgba(5,8,15,0.96); border-left:1px solid rgba(255,255,255,0.08);
    overflow-y:auto; z-index:9999; font:12px monospace;
    color:#c8d4f0; padding:12px; box-sizing:border-box;
    backdrop-filter:blur(12px);
  `;

  // Header
  panel.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">
      <div style="color:#f2c36f;font:700 13px monospace;letter-spacing:0.1em;">◈ ORACLE TUNING</div>
      <div style="color:#445;font-size:11px;">Ctrl+Shift+T to close</div>
    </div>
    <div style="color:#556;font-size:10px;margin-bottom:12px;line-height:1.5;">
      Live parameter editor — changes apply immediately.<br/>
      No redeploy needed. Document changes to behavior.js when done.
    </div>
    <div id="oracle-tuning-export" style="
      background:#0d1220;border:1px solid rgba(255,200,0,0.2);border-radius:6px;
      padding:8px;margin-bottom:14px;cursor:pointer;text-align:center;
      color:#f2c36f;font:600 11px monospace;
    ">⬇ Export tuned values to console</div>
  `;

  // Sections
  SECTIONS.forEach(sec => {
    const secEl = document.createElement("div");
    secEl.style.cssText = "margin-bottom:16px;";
    secEl.innerHTML = `
      <div style="color:${sec.color};font:700 11px monospace;letter-spacing:0.12em;
        border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:4px;margin-bottom:8px;">
        ${sec.label}
      </div>
    `;
    sec.params.forEach(([key, min, max, step, label]) => {
      const row = document.createElement("div");
      row.style.cssText = "margin-bottom:10px;";
      const val = LIVE_CONFIG[key];
      row.innerHTML = `
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
          <span style="color:#99a8c0;">${label}</span>
          <span id="tv_${key}" style="color:#f2c36f;min-width:40px;text-align:right;">${val}</span>
        </div>
        <input type="range" min="${min}" max="${max}" step="${step}" value="${val}"
          data-key="${key}"
          style="width:100%;height:4px;accent-color:${sec.color};cursor:pointer;"
        />
      `;
      secEl.appendChild(row);
    });
    panel.appendChild(secEl);
  });

  // Boolean toggles
  const booleans = [
    ["glowPulseRestrained",    "Glow pulse restrained"],
    ["broadcastPostureTight",  "Broadcast tight posture"],
    ["orbHaloPulseRestrained", "Orb halo restrained"],
    ["hairShimmerVisible",     "Hair shimmer ON"],
    ["hairEdgeGlowOnly",       "Hair edge glow only"],
  ];
  const boolSec = document.createElement("div");
  boolSec.innerHTML = `<div style="color:#aaa;font:700 11px monospace;letter-spacing:0.1em;
    border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:4px;margin-bottom:8px;">
    TOGGLES</div>`;
  booleans.forEach(([key, label]) => {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;";
    row.innerHTML = `
      <span style="color:#99a8c0;">${label}</span>
      <input type="checkbox" data-bool-key="${key}" ${LIVE_CONFIG[key] ? "checked" : ""}
        style="width:14px;height:14px;cursor:pointer;accent-color:#f2c36f;" />
    `;
    boolSec.appendChild(row);
  });
  panel.appendChild(boolSec);

  document.body.appendChild(panel);
  _panelEl = panel;

  // Slider events
  panel.querySelectorAll("input[type=range]").forEach(el => {
    el.addEventListener("input", (e) => {
      const key = e.target.dataset.key;
      const v   = parseFloat(e.target.value);
      LIVE_CONFIG[key] = v;
      const label = panel.querySelector(`#tv_${key}`);
      if (label) label.textContent = v.toFixed(step_precision(v));
    });
  });

  // Checkbox events
  panel.querySelectorAll("input[type=checkbox]").forEach(el => {
    el.addEventListener("change", (e) => {
      LIVE_CONFIG[e.target.dataset.boolKey] = e.target.checked;
    });
  });

  // Export button
  panel.querySelector("#oracle-tuning-export").addEventListener("click", () => {
    console.log("// ── ORACLE TUNING EXPORT ─────────────────────────────");
    Object.entries(LIVE_CONFIG).forEach(([k, v]) => {
      console.log(`  ${k.padEnd(28)}: ${JSON.stringify(v)},`);
    });
    console.log("// ── END EXPORT ─────────────────────────────────────────");
    panel.querySelector("#oracle-tuning-export").textContent = "✓ Exported to console";
    setTimeout(() => {
      panel.querySelector("#oracle-tuning-export").textContent = "⬇ Export tuned values to console";
    }, 2000);
  });
}

function step_precision(v) {
  const s = String(v);
  const d = s.indexOf(".");
  return d === -1 ? 0 : Math.min(s.length - d - 1, 3);
}
