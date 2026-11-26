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

vtype = os.environ.get("VIDEO_TYPE", "short").strip().lower()
style = os.environ.get("STYLE", "quiz").strip().lower()
is_long = (vtype == "long")

W, H = (1280, 720) if is_long else (720, 1280)
show_cap = "false" if is_long else "true"
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

if style == "quiz":
    n_scenes = 8 if is_long else 5
    prompt = f"""You are a viral YouTube Quiz / Would-You-Rather Shorts creator.
Create {n_scenes} fast-paced interactive quiz/dilemma rounds on: "{topic}"

Return ONLY valid JSON:
{{
  "scenes": [
    {{
      "narration": "Short punchy US English question under 130 chars.",
      "question": "Short 4-7 word question on screen",
      "opt_a": "Option A (2-4 words)",
      "opt_b": "Option B (2-4 words)",
      "pct_a": 68,
      "winner": "A"
    }}
  ]
}}"""
else:
    n_scenes = 12 if is_long else 7
    length_hint = "1-2 eerie US English sentences (140-210 chars)" if is_long else "1 chilling US English sentence (under 130 chars)"
    prompt = f"""You are a viral Dark Mystery / Scary Story YouTube narrator.
Break this topic into {n_scenes} suspenseful scenes: "{topic}"

Return ONLY valid JSON:
{{
  "scenes": [
    {{
      "narration": "{length_hint}",
      "clue_tag": "SHORT 1-3 WORD CLUE (e.g. 3:14 AM, NO SIGNAL, MISSING)",
      "mood": "rain"
    }}
  ]
}}
Allowed mood: "rain", "fog", "radar" """

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

QUIZ_HTML = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { margin:0; overflow:hidden; background:#0f0728; font-family:'Arial Black', Impact, sans-serif; color:#fff; }
  canvas { display:block; width:100vw; height:100vh; }
</style></head><body>
<canvas id="cv" width="__W__" height="__H__"></canvas>
<script>
const CFG = __CFG__;
const W = __W__, H = __H__;
const cv = document.getElementById("cv");
const ctx = cv.getContext("2d");

function roundCard(x, y, w, h, r, fill, stroke) {
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
  ctx.fillStyle = fill; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 6; ctx.stroke(); }
}

function wrapText(text, x, y, maxW, lh) {
  const words = (text || "").split(" ");
  let line = "", lines = [];
  for (const w of words) {
    const test = line ? line + " " + w : w;
    if (ctx.measureText(test).width > maxW && line) { lines.push(line); line = w; }
    else line = test;
  }
  if (line) lines.push(line);
  const startY = y - ((lines.length - 1) * lh) / 2;
  lines.forEach((l, i) => ctx.fillText(l, x, startY + i * lh));
}

window.renderAt = (t, d) => {
  const p = Math.min(1, t / Math.max(0.1, d));
  // Animated Purple/Indigo Gradient
  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, "#1e1b4b"); g.addColorStop(0.5, "#311042"); g.addColorStop(1, "#090d16");
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

  // Subtle Moving Grid
  ctx.strokeStyle = "rgba(255,255,255,0.05)"; ctx.lineWidth = 2;
  const off = (t * 25) % 60;
  for (let x = -60 + off; x < W; x += 60) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  for (let y = -60 + off; y < H; y += 60) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

  // Question Header
  const qScale = Math.min(1, p * 4);
  ctx.save(); ctx.translate(W/2, H*0.17); ctx.scale(qScale, qScale);
  roundCard(-W*0.43, -H*0.09, W*0.86, H*0.18, 26, "rgba(15,23,42,0.92)", "#facc15");
  ctx.fillStyle = "#ffffff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.font = `900 ${W<H ? 38 : 44}px Arial Black, sans-serif`;
  wrapText(CFG.question || "WHICH WOULD YOU PICK?", 0, 0, W*0.78, W<H ? 46 : 52);
  ctx.restore();

  // Countdown Bar (0 -> 0.68)
  const timerP = Math.max(0, 1 - p / 0.68);
  roundCard(W*0.1, H*0.30, W*0.8, 22, 11, "rgba(255,255,255,0.15)", null);
  if (timerP > 0) {
    roundCard(W*0.1, H*0.30, W*0.8 * timerP, 22, 11, timerP < 0.3 ? "#ef4444" : "#facc15", null);
  }

  // Option A & B Cards
  const reveal = p >= 0.68;
  const pctA = CFG.pct_a || 62;
  const pctB = 100 - pctA;
  const winA = (CFG.winner || "A") === "A";

  const cards = W < H
    ? [{x: W*0.08, y: H*0.36, w: W*0.84, h: H*0.21, col:"#2563eb", lbl:"A", txt:CFG.opt_a, pct:pctA, win:winA},
       {x: W*0.08, y: H*0.62, w: W*0.84, h: H*0.21, col:"#dc2626", lbl:"B", txt:CFG.opt_b, pct:pctB, win:!winA}]
    : [{x: W*0.06, y: H*0.38, w: W*0.41, h: H*0.44, col:"#2563eb", lbl:"A", txt:CFG.opt_a, pct:pctA, win:winA},
       {x: W*0.53, y: H*0.38, w: W*0.41, h: H*0.44, col:"#dc2626", lbl:"B", txt:CFG.opt_b, pct:pctB, win:!winA}];

  cards.forEach((c) => {
    const border = reveal ? (c.win ? "#22c55e" : "rgba(255,255,255,0.2)") : "#ffffff";
    const bg = reveal && !c.win ? "#1e293b" : c.col;
    roundCard(c.x, c.y, c.w, c.h, 28, bg, border);
    ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = `900 ${W<H ? 40 : 38}px Arial Black, sans-serif`;
    wrapText(c.txt || "", c.x + c.w/2, c.y + c.h*(reveal?0.38:0.5), c.w*0.85, 44);
    if (reveal) {
      ctx.fillStyle = c.win ? "#facc15" : "#cbd5e1";
      ctx.font = `900 ${W<H ? 54 : 50}px Arial Black, sans-serif`;
      ctx.fillText(c.pct + "%", c.x + c.w/2, c.y + c.h*0.74);
    }
  });
};
renderAt(0, 4);
</script></body></html>"""

MYSTERY_HTML = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { margin:0; overflow:hidden; background:#030407; font-family:'Arial Black', Impact, sans-serif; }
  canvas { display:block; width:100vw; height:100vh; }
  #cap { position:fixed; left:50%; top:68%; transform:translate(-50%,-50%); text-align:center;
         font-size:48px; font-weight:900; color:#fff; width:88%; line-height:1.12;
         text-shadow:0 4px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000; }
  .hi { color:#ef4444; transform:scale(1.15); display:inline-block; }
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

window.renderAt = (t, d) => {
  const p = Math.min(1, t / Math.max(0.1, d));
  ctx.fillStyle = "#04060b"; ctx.fillRect(0, 0, W, H);

  // Sweeping Flashlight Beam
  const lx = W * (0.5 + Math.sin(t * 1.4) * 0.25);
  const ly = H * (0.42 + Math.cos(t * 1.1) * 0.12);
  const beam = ctx.createRadialGradient(lx, ly, 10, lx, ly, Math.max(W, H) * 0.55);
  beam.addColorStop(0, "rgba(56,189,248,0.28)");
  beam.addColorStop(0.45, "rgba(15,23,42,0.18)");
  beam.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = beam; ctx.fillRect(0, 0, W, H);

  // Dark Pine Silhouettes at bottom
  ctx.fillStyle = "#020305";
  for (let i = 0; i < 14; i++) {
    const tx = (i / 13) * W;
    const th = H * (0.16 + (i % 3) * 0.06);
    ctx.beginPath(); ctx.moveTo(tx - 60, H); ctx.lineTo(tx, H - th); ctx.lineTo(tx + 60, H); ctx.fill();
  }

  // Rain / Fog / Radar
  if (CFG.mood === "radar") {
    ctx.strokeStyle = "rgba(239,68,68,0.35)"; ctx.lineWidth = 3;
    for (let r = 1; r <= 3; r++) {
      const rad = ((t * 90 + r * 90) % 280) + 30;
      ctx.beginPath(); ctx.arc(W*0.5, H*0.42, rad, 0, Math.PI*2); ctx.stroke();
    }
  } else {
    ctx.strokeStyle = "rgba(148,163,184,0.35)"; ctx.lineWidth = 2;
    for (let i = 0; i < 65; i++) {
      const rx = (i * 97 + t * 140) % W;
      const ry = (i * 61 + t * 540) % H;
      ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx - 6, ry + 22); ctx.stroke();
    }
  }

  // Clue Stamp (Top)
  if (CFG.clue_tag) {
    ctx.fillStyle = "rgba(220,38,38,0.9)";
    const bw = Math.min(W * 0.8, CFG.clue_tag.length * 28 + 50);
    ctx.beginPath(); ctx.roundRect(W/2 - bw/2, H*0.12, bw, 64, 10); ctx.fill();
    ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "900 34px Arial Black, sans-serif";
    ctx.fillText(CFG.clue_tag.toUpperCase(), W/2, H*0.12 + 32);
  }

  if (SHOW_CAP && WORDS.length) {
    const wi = Math.min(WORDS.length - 1, Math.floor(p * WORDS.length));
    const start = Math.max(0, wi - 1);
    document.getElementById("cap").innerHTML = WORDS.slice(start, start + 3)
      .map((w, i) => (start + i === wi) ? `<span class='hi'>${w}</span>` : w).join(" ");
  }
};
renderAt(0, 4);
</script></body></html>"""

tpl = QUIZ_HTML if style == "quiz" else MYSTERY_HTML
story_scenes = []
for sc in plan["scenes"]:
    html = (tpl
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
print(f"Generated {len(story_scenes)} ({style}/{vtype}) scenes for: {topic}")
