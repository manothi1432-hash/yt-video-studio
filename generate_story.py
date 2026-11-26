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
    prompt = f"""You are a viral YouTube Shorts riddle & mystery storyteller.
Create a 5-scene gripping story/mystery/riddle on: "{topic}"
- Scenes 1 to 4: Tell the story/clues fast (type="story").
- Scene 5 (FINAL SCENE): Do NOT reveal the answer! Ask the final question on screen and end the narration with "Comment your answer below!" (type="question").

Return ONLY valid JSON:
{{
  "scenes": [
    {{
      "type": "story",
      "narration": "Short punchy US English story sentence under 130 chars.",
      "clue_tag": "CLUE 1",
      "question": "",
      "options": []
    }},
    {{
      "type": "question",
      "narration": "So which one is it? Comment your answer below!",
      "clue_tag": "YOUR TURN",
      "question": "Short 5-8 word final question?",
      "options": ["A) Choice 1", "B) Choice 2", "C) Choice 3"]
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
      "type": "story",
      "narration": "{length_hint}",
      "clue_tag": "SHORT 1-3 WORD CLUE (e.g. 3:14 AM, NO SIGNAL, MISSING)",
      "question": "",
      "options": []
    }}
  ]
}}"""

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
  body { margin:0; overflow:hidden; background:#05040f; font-family:'Arial Black', Impact, sans-serif; color:#fff; }
  canvas { display:block; width:100vw; height:100vh; }
  #cap { position:fixed; left:50%; top:66%; transform:translate(-50%,-50%); text-align:center;
         font-size:48px; font-weight:900; color:#fff; width:88%; line-height:1.12;
         text-shadow:0 4px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000; }
  .hi { color:#facc15; transform:scale(1.15); display:inline-block; }
</style></head><body>
<canvas id="cv" width="__W__" height="__H__"></canvas>
<div id="cap"></div>
<script>
const CFG = __CFG__;
const W = __W__, H = __H__;
const SHOW_CAP = __SHOW_CAP__;
const IS_Q = (CFG.type === "question");
if (!SHOW_CAP || IS_Q) document.getElementById("cap").style.display = "none";

const cv = document.getElementById("cv");
const ctx = cv.getContext("2d");
const WORDS = CFG.narration.split(/\s+/).filter(Boolean);

function roundCard(x, y, w, h, r, fill, stroke, lw=4) {
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
  ctx.fillStyle = fill; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
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
  ctx.fillStyle = "#05040f"; ctx.fillRect(0, 0, W, H);

  // Drifting Neon Spotlight
  const lx = W * (0.5 + Math.sin(t * 1.3) * 0.22);
  const ly = H * (0.40 + Math.cos(t * 1.1) * 0.12);
  const rg = ctx.createRadialGradient(lx, ly, 10, lx, ly, Math.max(W, H) * 0.58);
  rg.addColorStop(0, IS_Q ? "rgba(168,85,247,0.38)" : "rgba(56,189,248,0.28)");
  rg.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);

  if (IS_Q) {
    // Final Cliffhanger Question Card
    const pop = Math.min(1, p * 5);
    ctx.save(); ctx.translate(W/2, H*0.24); ctx.scale(0.88 + pop*0.12, 0.88 + pop*0.12);
    roundCard(-W*0.44, -H*0.11, W*0.88, H*0.22, 28, "rgba(15,23,42,0.88)", "#facc15", 4);
    ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = `900 ${W<H ? 38 : 42}px Arial Black, sans-serif`;
    wrapText(CFG.question || "WHAT WOULD YOU DO?", 0, 0, W*0.78, 46);
    ctx.restore();

    // Options (No Answer Revealed!)
    const opts = CFG.options || [];
    const cols = ["#2563eb", "#7c3aed", "#dc2626"];
    opts.slice(0, 3).forEach((o, i) => {
      const oy = H * 0.41 + i * (H * 0.11 + 16);
      roundCard(W*0.08, oy, W*0.84, H*0.105, 22, "rgba(255,255,255,0.10)", cols[i % 3], 3);
      ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.font = `900 ${W<H ? 30 : 32}px Arial Black, sans-serif`;
      ctx.fillText(String(o).slice(0, 30), W/2, oy + (H*0.105)/2);
    });

    // Pulsing Comment CTA Badge
    const pulse = 1 + Math.sin(t * 7) * 0.05;
    ctx.save(); ctx.translate(W/2, H*0.84); ctx.scale(pulse, pulse);
    roundCard(-W*0.40, -38, W*0.80, 76, 38, "#facc15", "#fff", 3);
    ctx.fillStyle = "#000"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = `900 ${W<H ? 28 : 30}px Arial Black, sans-serif`;
    ctx.fillText("COMMENT YOUR ANSWER!", 0, 2);
    ctx.restore();
  } else {
    // Story Mode: Subtle Rain + Clue Tag + Pop Captions
    ctx.strokeStyle = "rgba(148,163,184,0.28)"; ctx.lineWidth = 2;
    for (let i = 0; i < 55; i++) {
      const rx = (i * 97 + t * 130) % W;
      const ry = (i * 61 + t * 520) % H;
      ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx - 6, ry + 22); ctx.stroke();
    }
    if (CFG.clue_tag) {
      const bw = Math.min(W * 0.8, CFG.clue_tag.length * 26 + 50);
      roundCard(W/2 - bw/2, H*0.14, bw, 60, 14, "rgba(220,38,38,0.88)", "#fff", 2);
      ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.font = "900 30px Arial Black, sans-serif";
      ctx.fillText(CFG.clue_tag.toUpperCase(), W/2, H*0.14 + 30);
    }
    if (SHOW_CAP && WORDS.length) {
      const wi = Math.min(WORDS.length - 1, Math.floor(p * WORDS.length));
      const start = Math.max(0, wi - 1);
      document.getElementById("cap").innerHTML = WORDS.slice(start, start + 3)
        .map((w, i) => (start + i === wi) ? `<span class='hi'>${w}</span>` : w).join(" ");
    }
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
print(f"Generated {len(story_scenes)} ({style}/{vtype}) cliffhanger scenes for: {topic}")
