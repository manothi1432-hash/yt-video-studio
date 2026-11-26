
import os
import json
import time
from pathlib import Path
from google import genai
from google.genai import types

topic = os.environ.get("TOPIC", "").strip()
if not topic:
    print("No topic provided, keeping existing story.json")
    raise SystemExit(0)

vtype = os.environ.get("VIDEO_TYPE", "long").strip().lower()
is_long = (vtype == "long")

W, H = (1280, 720) if is_long else (720, 1280)
scene_count = 12 if is_long else 8
show_cap = "false" if is_long else "true"
length_hint = "1-2 suspenseful US English sentences (140-210 chars)" if is_long else "1 punchy US English sentence (under 130 chars)"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = f"""You are a viral dark-stickman YouTube storyteller.
Break this topic into {scene_count} suspenseful action scenes: "{topic}"

Return ONLY valid JSON:
{{
  "scenes": [
    {{
      "narration": "{length_hint}",
      "pose": "climb_cliff",
      "accent": "#fde047",
      "camera": "zoom_in"
    }}
  ]
}}

Allowed values:
- pose: "climb_cliff" (stickman climbing sheer cliff edge with grappling hook), "dangle_rope" (hanging from rope over abyss), "run_fast" (sprinting across dark ground), "fall_abyss" (falling into deep chasm), "crouch_sneak" (sneaking on ledge), "point_up" (standing on edge pointing)
- accent: "#fde047" (glowing gold), "#38bdf8" (glowing cyan), "#ef4444" (danger red)
- camera: "zoom_in", "pan_up", "pan_down", "drift_right" """

MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
resp = None
last_err = None
for m in MODELS:
    for attempt in range(2):
        try:
            print(f"Trying {m} (attempt {attempt + 1})...")
            resp = client.models.generate_content(
                model=m, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            print(f"Success with {m}!")
            break
        except Exception as e:
            last_err = e
            print(f"{m} failed: {e}")
            time.sleep(5)
    if resp is not None:
        break

if resp is None:
    raise RuntimeError(f"All models failed: {last_err}")

plan = json.loads(resp.text)

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { margin:0; overflow:hidden; background:#05060a; font-family:'Arial Black', Impact, sans-serif; }
  canvas { display:block; width:100vw; height:100vh; }
  #cap { position:fixed; left:50%; top:72%; transform:translate(-50%,-50%); text-align:center;
         font-size:48px; font-weight:900; color:#fff; width:88%; line-height:1.12;
         text-shadow:0 4px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000; }
  .hi { color:#facc15; transform:scale(1.14); display:inline-block; }
</style></head><body>
<canvas id="cv" width="__W__" height="__H__"></canvas>
<div id="cap"></div>
<script>
const CFG = __CFG__;
const W = __W__, H = __H__;
const SHOW_CAP = __SHOW_CAP__;
if (!SHOW_CAP) document.getElementById("cap").style.display = "none";

const cv = document.getElementById("cv");
const ctx = cv.getContext("2d");
const WORDS = CFG.narration.split(/\s+/).filter(Boolean);
const ACCENT = CFG.accent || "#fde047";

function seg(x1, y1, x2, y2) {
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
}

function drawGlowStickman(cx, cy, sc, t, pose) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(sc, sc);
  ctx.lineCap = "round"; ctx.lineJoin = "round";
  ctx.strokeStyle = "#ffffff"; ctx.fillStyle = "#ffffff";
  ctx.shadowColor = "rgba(255,255,255,0.85)"; ctx.shadowBlur = 22;
  ctx.lineWidth = 14;

  const breath = Math.sin(t * 4) * 2;
  if (pose === "climb_cliff") {
    const pull = Math.sin(t * 5) * 8;
    // Head & Torso
    ctx.beginPath(); ctx.arc(-18, -62 + pull, 18, 0, Math.PI*2); ctx.fill();
    seg(-6, -42 + pull, -6, 18 + pull);
    // Arms gripping ledge
    seg(-6, -34 + pull, 22, -55); seg(22, -55, 22, -62);
    seg(-6, -24 + pull, 16, -26);
    // Bent knees against cliff wall
    seg(-6, 18 + pull, -28, 38 + pull); seg(-28, 38 + pull, -6, 68 + pull);
    seg(-6, 18 + pull, 18, 42 + pull); seg(18, 42 + pull, 2, 74 + pull);
  } else if (pose === "dangle_rope") {
    const sw = Math.sin(t * 2.8) * 14;
    ctx.beginPath(); ctx.arc(sw, -65, 18, 0, Math.PI*2); ctx.fill();
    seg(sw, -45, sw * 0.7, 15);
    seg(sw, -35, 0, -78);
    seg(sw * 0.7, 15, sw - 16, 55); seg(sw - 16, 55, sw - 6, 82);
    seg(sw * 0.7, 15, sw + 18, 52); seg(sw + 18, 52, sw + 10, 80);
  } else if (pose === "run_fast") {
    const s = Math.sin(t * 11);
    const b = Math.abs(Math.cos(t * 11)) * 6;
    ctx.beginPath(); ctx.arc(14, -64 - b, 18, 0, Math.PI*2); ctx.fill();
    seg(10, -44 - b, -8, 12 - b);
    // Arms pumping
    seg(4, -34 - b, 28 * s, -10 - b); seg(28 * s, -10 - b, 42 * s, -22 - b);
    seg(4, -34 - b, -26 * s, -10 - b);
    // Legs sprinting
    seg(-8, 12 - b, 26 * s, 45 - b); seg(26 * s, 45 - b, 14 * s - 12, 82);
    seg(-8, 12 - b, -26 * s, 45 - b); seg(-26 * s, 45 - b, -36 * s, 82);
  } else if (pose === "fall_abyss") {
    const fl = Math.sin(t * 14) * 12;
    ctx.beginPath(); ctx.arc(0, -55, 18, 0, Math.PI*2); ctx.fill();
    seg(0, -35, 4, 20);
    seg(2, -25, -36, -50 + fl); seg(2, -25, 38, -48 - fl);
    seg(4, 20, -24, 65 - fl); seg(4, 20, 28, 62 + fl);
  } else if (pose === "crouch_sneak") {
    ctx.beginPath(); ctx.arc(8, -26 + breath, 18, 0, Math.PI*2); ctx.fill();
    seg(4, -8 + breath, -12, 26 + breath);
    seg(0, 2 + breath, 26, 22 + breath);
    seg(-12, 26 + breath, 12, 48); seg(12, 48, 4, 78);
    seg(-12, 26 + breath, -28, 52); seg(-28, 52, -24, 78);
  } else {
    // point_up
    ctx.beginPath(); ctx.arc(0, -64 + breath, 18, 0, Math.PI*2); ctx.fill();
    seg(0, -44 + breath, 0, 16 + breath);
    seg(0, -34 + breath, -26, 4 + breath);
    seg(0, -34 + breath, 34, -56 + Math.sin(t*4)*5);
    seg(0, 16 + breath, -18, 78); seg(0, 16 + breath, 18, 78);
  }
  ctx.restore();
}

function drawGlowingLedge(x, y, w, h) {
  ctx.fillStyle = "#0a0c12";
  ctx.fillRect(x, y, w, h);
  ctx.save();
  ctx.strokeStyle = ACCENT; ctx.lineWidth = 3;
  ctx.shadowColor = ACCENT; ctx.shadowBlur = 14;
  ctx.strokeRect(x, y, w, h);
  ctx.restore();
}

window.renderAt = (t, d) => {
  const p = Math.min(1, t / Math.max(0.1, d));
  const pose = CFG.pose || "climb_cliff";

  // Dark Vignette Sky
  const grad = ctx.createRadialGradient(W*0.5, H*0.45, 40, W*0.5, H*0.5, Math.max(W, H)*0.75);
  grad.addColorStop(0, "#131722"); grad.addColorStop(1, "#030407");
  ctx.fillStyle = grad; ctx.fillRect(0, 0, W, H);

  // Subtle Floating Dust Particles
  ctx.fillStyle = "rgba(255,255,255,0.22)";
  for (let i=0; i<28; i++) {
    const dx = (i * 137 + t * 18) % W;
    const dy = (i * 89 + t * (pose==="fall_abyss"?-160:12) + H) % H;
    ctx.beginPath(); ctx.arc(dx, dy, 1.5 + (i%2), 0, Math.PI*2); ctx.fill();
  }

  ctx.save();
  let z = 1.0 + p * 0.14;
  let py = 0, px = 0;
  if (CFG.camera === "pan_up") py = (1 - p) * 35;
  else if (CFG.camera === "pan_down") py = -p * 35;
  else if (CFG.camera === "drift_right") px = -p * 30;
  ctx.translate(W/2 + px, H/2 + py); ctx.scale(z, z); ctx.translate(-W/2, -H/2);

  const sc = W < H ? 1.15 : 1.25;
  if (pose === "climb_cliff") {
    drawGlowingLedge(-10, H*0.52, W*0.24, H*0.55);
    drawGlowingLedge(W*0.56, H*0.46, W*0.48, H*0.60);
    // Grappling Hook
    ctx.save(); ctx.strokeStyle = "#cbd5e1"; ctx.lineWidth = 4;
    ctx.shadowColor = "#fff"; ctx.shadowBlur = 8;
    seg(W*0.56 + 18, H*0.46 - 2, W*0.56 + 18, H*0.46 - 20);
    ctx.beginPath(); ctx.arc(W*0.56 + 18, H*0.46 - 14, 12, 0, Math.PI); ctx.stroke();
    ctx.restore();
    drawGlowStickman(W*0.52, H*0.48, sc, t, pose);
  } else if (pose === "dangle_rope") {
    ctx.save(); ctx.strokeStyle = ACCENT; ctx.lineWidth = 4;
    ctx.shadowColor = ACCENT; ctx.shadowBlur = 12;
    seg(W*0.5, 0, W*0.5, H*0.42);
    ctx.restore();
    drawGlowStickman(W*0.5, H*0.48, sc, t, pose);
  } else if (pose === "fall_abyss") {
    drawGlowingLedge(-10, -10, W*0.22, H+20);
    drawGlowingLedge(W*0.78, -10, W*0.25, H+20);
    drawGlowStickman(W*0.5, H*0.42 + p*45, sc, t, pose);
  } else {
    drawGlowingLedge(-10, H*0.62, W+20, H*0.45);
    const sx = pose === "run_fast" ? W*(0.35 + p*0.3) : W*0.5;
    drawGlowStickman(sx, H*0.62 - 80*sc, sc, t, pose);
  }
  ctx.restore();

  if (SHOW_CAP && WORDS.length) {
    const wi = Math.min(WORDS.length - 1, Math.floor(p * WORDS.length));
    const start = Math.max(0, wi - 1);
    document.getElementById("cap").innerHTML = WORDS.slice(start, start + 3)
      .map((w, i) => (start + i === wi) ? `<span class='hi'>${w}</span>` : w).join(" ");
  }
};
renderAt(0, 4);
</script></body></html>"""

story_scenes = []
for sc in plan["scenes"]:
    html = (HTML_TEMPLATE
            .replace("__CFG__", json.dumps(sc))
            .replace("__W__", str(W))
            .replace("__H__", str(H))
            .replace("__SHOW_CAP__", show_cap))
    story_scenes.append({
        "narration": sc["narration"],
        "html": html
    })

out = {"width": W, "height": H, "voice": "en-US-AndrewMultilingualNeural", "scenes": story_scenes}
Path("story.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Generated {len(story_scenes)} ({vtype}) Glowing Neon Stickman scenes for: {topic}")
