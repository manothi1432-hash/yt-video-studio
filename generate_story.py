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
scene_count = 14 if is_long else 8
show_cap = "false" if is_long else "true"
length_hint = "1-2 crisp, dramatic US English sentences (140-220 chars) for fast 5-8s cuts" if is_long else "1 punchy US English sentence (under 130 chars)"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = f"""You are a viral YouTube explainer director (like @fakeexplainer96).
Break this topic into {scene_count} fast-paced visual scenes: "{topic}"

Return ONLY valid JSON with this exact schema:
{{
  "scenes": [
    {{
      "narration": "{length_hint}",
      "scene": "rain_field",
      "mood": "dark",
      "pose": "shiver",
      "impact_text": "",
      "has_group": false
    }}
  ]
}}

Allowed values:
- scene: "rain_field" (pouring rain outdoors), "cave_fire" (warm campfire inside dark cave), "river_flood" (rising muddy river), "stickman_talk" (clean gray background closeup talking stickman), "cliff_edge" (explorer on cliff), "snow_trail" (icy mountain path)
- mood: "dark", "warm", "gray"
- pose: "shiver", "point", "shrug", "sit_sad", "walk", "spear"
- impact_text: optional 1-2 word dramatic red/black text at top (e.g. "DEATH", "TRAPPED", "NO ESCAPE") on 2-3 key scenes, else ""
- has_group: true or false (add 3-4 extra stick-figures around fire or walking)"""

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
  body { margin:0; overflow:hidden; background:#111; font-family:'Arial Black', Impact, sans-serif; }
  canvas { display:block; width:100vw; height:100vh; }
  #cap { position:fixed; left:50%; top:64%; transform:translate(-50%,-50%); text-align:center;
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

function drawStickman(x, y, s, t, pose, talking=true) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  const shiv = pose === "shiver" ? Math.sin(t * 38) * 3 : 0;
  const bob = Math.sin(t * 6) * 4;
  const talk = talking ? Math.abs(Math.sin(t * 14)) : 0;
  const blink = (Math.floor(t * 2.3) % 7 === 0);

  ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = "#111"; ctx.lineWidth = 8;

  // Legs
  if (pose === "sit_sad") {
    ctx.beginPath(); ctx.moveTo(-12, 85); ctx.lineTo(-42, 130); ctx.lineTo(-18, 155); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(12, 85); ctx.lineTo(42, 130); ctx.lineTo(18, 155); ctx.stroke();
  } else {
    const walk = pose === "walk" ? Math.sin(t * 7) * 22 : 0;
    ctx.beginPath(); ctx.moveTo(-10+shiv, 85); ctx.lineTo(-22+walk, 165); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(10+shiv, 85); ctx.lineTo(22-walk, 165); ctx.stroke();
  }

  // Body / Fur Tunic
  if (CFG.scene !== "stickman_talk") {
    ctx.fillStyle = "#b45309";
    ctx.beginPath(); ctx.moveTo(-26+shiv, 15+bob); ctx.lineTo(26+shiv, 15+bob);
    ctx.lineTo(34+shiv, 95+bob); ctx.lineTo(-34+shiv, 95+bob); ctx.closePath();
    ctx.fill(); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.moveTo(0, 10+bob); ctx.lineTo(0, 95+bob); ctx.stroke();
  }

  // Arms
  if (pose === "point") {
    ctx.beginPath(); ctx.moveTo(0, 28+bob); ctx.lineTo(-45, 55+bob); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, 28+bob); ctx.lineTo(52, 8+bob+Math.sin(t*5)*8); ctx.stroke();
  } else if (pose === "shrug") {
    ctx.beginPath(); ctx.moveTo(0, 28+bob); ctx.lineTo(-48, 38+bob); ctx.lineTo(-58, 12+bob); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, 28+bob); ctx.lineTo(48, 38+bob); ctx.lineTo(58, 12+bob); ctx.stroke();
  } else if (pose === "spear") {
    ctx.beginPath(); ctx.moveTo(0, 28+bob); ctx.lineTo(42, 42+bob); ctx.stroke();
    ctx.strokeStyle = "#78350f"; ctx.lineWidth = 7;
    ctx.beginPath(); ctx.moveTo(42, -55+bob); ctx.lineTo(42, 135); ctx.stroke();
    ctx.fillStyle = "#94a3b8"; ctx.strokeStyle = "#111"; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(32, -55+bob); ctx.lineTo(42, -85+bob); ctx.lineTo(52, -55+bob); ctx.closePath(); ctx.fill(); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.moveTo(-18+shiv, 28+bob); ctx.lineTo(-38+shiv, 68+bob); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(18+shiv, 28+bob); ctx.lineTo(38+shiv, 68+bob); ctx.stroke();
  }

  // Head
  ctx.fillStyle = "#fff7ed"; ctx.strokeStyle = "#111"; ctx.lineWidth = 8;
  ctx.beginPath(); ctx.arc(shiv, -38+bob, 48, 0, Math.PI*2); ctx.fill(); ctx.stroke();

  // Hair for outdoor caveman
  if (CFG.scene !== "stickman_talk") {
    ctx.fillStyle = "#1c1917";
    ctx.beginPath(); ctx.arc(shiv, -52+bob, 46, Math.PI*1.05, Math.PI*1.95); ctx.fill();
  }

  // Eyes & Brows
  ctx.fillStyle = "#111";
  if (blink) {
    ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(-24+shiv,-42+bob); ctx.lineTo(-8+shiv,-42+bob);
    ctx.moveTo(8+shiv,-42+bob); ctx.lineTo(24+shiv,-42+bob); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.arc(-16+shiv, -42+bob, 5.5, 0, Math.PI*2); ctx.arc(16+shiv, -42+bob, 5.5, 0, Math.PI*2); ctx.fill();
  }
  ctx.lineWidth = 5;
  ctx.beginPath(); ctx.moveTo(-26+shiv, -56+bob); ctx.lineTo(-6+shiv, -52+bob); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(6+shiv, -52+bob); ctx.lineTo(26+shiv, -56+bob); ctx.stroke();

  // Mouth
  ctx.fillStyle = "#7f1d1d"; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.ellipse(shiv, -14+bob, 11, 3 + talk*8, 0, 0, Math.PI*2); ctx.fill(); ctx.stroke();
  ctx.restore();
}

window.renderAt = (t, d) => {
  const p = Math.min(1, t / Math.max(0.1, d));
  const sc = CFG.scene || "rain_field";
  ctx.clearRect(0, 0, W, H);

  ctx.save();
  const zoom = 1.0 + p * 0.08;
  ctx.translate(W/2, H/2); ctx.scale(zoom, zoom); ctx.translate(-W/2, -H/2);

  if (sc === "stickman_talk") {
    ctx.fillStyle = "#d6d3d1"; ctx.fillRect(0, 0, W, H);
    drawStickman(W*0.5, H*0.56, W<H ? 1.8 : 2.1, t, CFG.pose || "point", true);
  } else if (sc === "cave_fire") {
    ctx.fillStyle = "#1c1917"; ctx.fillRect(0, 0, W, H);
    // Cave opening
    ctx.fillStyle = "#334155";
    ctx.beginPath(); ctx.arc(W*0.5, H*0.65, W*0.42, Math.PI, 0); ctx.fill();
    ctx.fillStyle = "#44403c"; ctx.fillRect(0, H*0.68, W, H*0.32);
    // Flickering Campfire
    const fl = Math.sin(t*18)*8;
    ctx.fillStyle = "#f97316";
    ctx.beginPath(); ctx.moveTo(W*0.45, H*0.76); ctx.lineTo(W*0.5, H*0.56+fl); ctx.lineTo(W*0.55, H*0.76); ctx.fill();
    ctx.fillStyle = "#facc15";
    ctx.beginPath(); ctx.moveTo(W*0.47, H*0.76); ctx.lineTo(W*0.5, H*0.62-fl*0.6); ctx.lineTo(W*0.53, H*0.76); ctx.fill();
    drawStickman(W*0.3, H*0.62, 1.15, t, "sit_sad", true);
    if (CFG.has_group) drawStickman(W*0.7, H*0.62, 1.15, t+1, "sit_sad", false);
  } else if (sc === "river_flood") {
    ctx.fillStyle = "#64748b"; ctx.fillRect(0, 0, W, H*0.55);
    ctx.fillStyle = "#78716c"; ctx.fillRect(0, H*0.5, W*0.42, H*0.5);
    ctx.fillStyle = "#b45309";
    ctx.beginPath(); ctx.moveTo(W*0.35, H*0.52);
    for(let x=W*0.35; x<=W; x+=40) ctx.lineTo(x, H*0.62 + Math.sin(x*0.03 + t*5)*12);
    ctx.lineTo(W, H); ctx.lineTo(W*0.35, H); ctx.closePath(); ctx.fill();
    drawStickman(W*0.24, H*0.46, 1.25, t, CFG.pose || "spear", true);
  } else {
    // Rain / Cliff / Snow outdoor
    const isSnow = (sc === "snow_trail");
    ctx.fillStyle = isSnow ? "#cbd5e1" : "#64748b"; ctx.fillRect(0, 0, W, H*0.62);
    ctx.fillStyle = isSnow ? "#e2e8f0" : "#78350f"; ctx.fillRect(0, H*0.62, W, H*0.38);
    ctx.strokeStyle = "#451a03"; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(0, H*0.62); ctx.lineTo(W, H*0.62); ctx.stroke();
    drawStickman(W*0.5, H*0.54, W<H ? 1.35 : 1.45, t, CFG.pose || "shiver", true);
    if (CFG.has_group) drawStickman(W*0.25, H*0.55, 1.1, t+0.8, "walk", false);
    // Rain or Snow streaks
    ctx.strokeStyle = isSnow ? "rgba(255,255,255,0.85)" : "rgba(226,232,240,0.55)";
    ctx.lineWidth = isSnow ? 4 : 2.5;
    for (let i=0; i<55; i++) {
      const rx = (i * 97 + t * (isSnow ? 40 : 180)) % W;
      const ry = (i * 61 + t * (isSnow ? 160 : 620)) % H;
      ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx - (isSnow?2:8), ry + (isSnow?5:24)); ctx.stroke();
    }
  }

  // Big Red Impact Word (like "Death" in @fakeexplainer96)
  if (CFG.impact_text) {
    ctx.fillStyle = "#dc2626"; ctx.strokeStyle = "#000"; ctx.lineWidth = 10;
    ctx.font = `900 ${W<H ? 68 : 88}px Arial Black, Impact, sans-serif`;
    ctx.textAlign = "center";
    ctx.strokeText(CFG.impact_text, W*0.5, H*0.18);
    ctx.fillText(CFG.impact_text, W*0.5, H*0.18);
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

out = {"width": W, "height": H, "voice": "en-US-BrianMultilingualNeural", "scenes": story_scenes}
Path("story.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Generated {len(story_scenes)} ({vtype}) @fakeexplainer96-style scenes for: {topic}")
