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
is_long = (vtype == "long")

W, H = (1280, 720) if is_long else (720, 1280)
scene_count = 14 if is_long else 8
show_cap = "false" if is_long else "true"
length_hint = "2-3 engaging US English sentences (250-350 chars)" if is_long else "1 punchy US English sentence (under 140 chars)"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = f"""You are a viral YouTube video director (RicksClips / ToonWright style).
Break this topic into {scene_count} scenes: "{topic}"

Return ONLY valid JSON with this exact schema:
{{
  "scenes": [
    {{
      "narration": "{length_hint}",
      "setting": "ocean_ship",
      "sky": "day",
      "camera_move": "dolly_in",
      "hat": "tophat",
      "shirt_color": "#b91c1c",
      "emotion": "determined",
      "action": "walk",
      "prop": "ice_block",
      "headline": "A SHIP FULL OF ICE?!"
    }}
  ]
}}

Allowed values:
- setting: "ocean_ship", "town_bridge", "ice_pond", "city_street", "forest_camp", "office_room"
- sky: "day", "sunset", "night"
- camera_move: "dolly_in", "orbit_left", "orbit_right", "closeup", "pan_up"
- hat: "tophat", "cap", "crown", "none"
- emotion: "happy", "shocked", "smug", "determined", "sad"
- action: "walk", "wave", "point", "talk"
- prop: "ice_block", "newspaper", "gold_coin", "map", "none"
- headline: short 2-4 word newspaper text if prop is newspaper, else "" """

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
  body { margin:0; overflow:hidden; background:#000; font-family: 'Arial Black', Impact, sans-serif; }
  #cap { position:fixed; left:50%; top:58%; transform:translate(-50%,-50%); text-align:center;
         font-size:48px; font-weight:900; color:#fff; text-shadow: 0 4px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000;
         pointer-events:none; width:88%; line-height:1.1; }
  .hi { color:#facc15; transform:scale(1.12); display:inline-block; }
</style>
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
</head><body>
<div id="cap"></div>
<script>
const CFG = __CFG__;
const W = __W__, H = __H__;
const SHOW_CAP = __SHOW_CAP__;
if (!SHOW_CAP) document.getElementById("cap").style.display = "none";

const scene = new THREE.Scene();
const skyColors = { day: 0x67b7f7, sunset: 0xf97316, night: 0x0f172a };
scene.background = new THREE.Color(skyColors[CFG.sky] || 0x67b7f7);
scene.fog = new THREE.Fog(scene.background, 12, 48);

const camera = new THREE.PerspectiveCamera(48, W/H, 0.1, 100);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.75));
const sun = new THREE.DirectionalLight(0xfffbeb, 1.2);
sun.position.set(8, 14, 10);
sun.castShadow = true;
scene.add(sun);

const isWater = (CFG.setting === "ocean_ship" || CFG.setting === "town_bridge");
const groundGeo = new THREE.PlaneGeometry(80, 80, 16, 16);
const groundMat = new THREE.MeshStandardMaterial({ color: isWater ? 0x0284c7 : 0x4d7c0f, roughness: isWater ? 0.2 : 0.9 });
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

function box(w,h,d,col,x,y,z,ry=0){
  const m = new THREE.Mesh(new THREE.BoxGeometry(w,h,d), new THREE.MeshStandardMaterial({color:col}));
  m.position.set(x,y,z); m.rotation.y=ry; m.castShadow=true; m.receiveShadow=true; scene.add(m); return m;
}
function cyl(rt,rb,h,col,x,y,z){
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt,rb,h,12), new THREE.MeshStandardMaterial({color:col}));
  m.position.set(x,y,z); m.castShadow=true; scene.add(m); return m;
}

if (CFG.setting === "ocean_ship") {
  box(4.5, 0.4, 10, 0x78350f, 0, 0.3, 1);
  box(5, 1.8, 11, 0x451a03, 0, 0.9, -7, 0.2);
  cyl(0.15, 0.18, 7, 0x78350f, 0, 4.5, -7);
  box(3.4, 2.8, 0.1, 0xfef3c7, 0, 5.2, -6.7, 0.2);
  box(1.1, 1.1, 1.1, 0xbae6fd, -1.3, 0.9, 1.2);
} else if (CFG.setting === "town_bridge") {
  box(14, 0.4, 3.2, 0x78350f, 0, 0.8, 0);
  box(5, 3.5, 4, 0xd6d3d1, -5, 1.75, -5);
  box(5, 4.2, 4, 0xfef3c7, 5, 2.1, -6);
  box(5.6, 1.6, 4.6, 0x991b1b, -5, 4.2, -5);
  box(5.6, 1.6, 4.6, 0x1e3a8a, 5, 4.9, -6);
} else if (CFG.setting === "ice_pond") {
  box(14, 0.2, 14, 0xbae6fd, 0, 0.05, 0);
  for(let i=-2;i<=2;i++) box(1.2, 1.2, 1.2, 0x7dd3fc, i*1.6, 0.7, -3);
  for(let i=-1;i<=1;i++) box(1.2, 1.2, 1.2, 0x38bdf8, i*1.6, 1.9, -3);
} else if (CFG.setting === "city_street") {
  box(40, 0.1, 5, 0x334155, 0, 0.06, 0);
  box(4, 9, 4, 0x64748b, -5, 4.5, -6);
  box(5, 12, 4, 0x475569, 4, 6, -7);
  box(3.5, 7, 3.5, 0x94a3b8, 0, 3.5, -9);
} else if (CFG.setting === "office_room") {
  box(16, 8, 0.3, 0xf1f5f9, 0, 4, -5);
  box(4, 1.2, 2, 0x78350f, 0, 0.6, -2);
  box(1.6, 1.0, 0.1, 0x1e293b, 0, 1.7, -2);
} else {
  for(let i=-3;i<=3;i+=2){ cyl(0.2,0.3,2.5,0x78350f,i*2,1.2,-4); box(2,2.5,2,0x15803d,i*2,3.2,-4); }
}

const c2 = document.createElement("canvas");
c2.width = 512; c2.height = 640;
const ctx = c2.getContext("2d");
const tex = new THREE.CanvasTexture(c2);
const charMat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, side: THREE.DoubleSide });
const charMesh = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 3.25), charMat);
charMesh.position.set(0, 1.8, 1.2);
scene.add(charMesh);

function drawChar(t, d) {
  ctx.clearRect(0, 0, 512, 640);
  const bob = Math.abs(Math.sin(t * 7)) * 10;
  const talk = Math.abs(Math.sin(t * 14));
  const blink = (Math.floor(t * 2.5) % 7 === 0);
  const legSwing = CFG.action === "walk" ? Math.sin(t * 7) * 28 : 0;
  const armWave = (CFG.action === "wave" || CFG.action === "point") ? Math.sin(t * 6) * 35 : Math.sin(t * 3) * 10;

  ctx.lineCap = "round"; ctx.lineJoin = "round";
  ctx.strokeStyle = "#111"; ctx.lineWidth = 14;
  ctx.beginPath(); ctx.moveTo(235, 420-bob); ctx.lineTo(220+legSwing, 570); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(277, 420-bob); ctx.lineTo(292-legSwing, 570); ctx.stroke();

  ctx.beginPath(); ctx.moveTo(205, 315-bob); ctx.lineTo(140, 385-bob-armWave); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(307, 315-bob); ctx.lineTo(372, 375-bob+armWave*0.5); ctx.stroke();

  ctx.fillStyle = CFG.shirt_color || "#b91c1c";
  ctx.strokeStyle = "#111"; ctx.lineWidth = 10;
  ctx.beginPath(); ctx.roundRect(198, 290-bob, 116, 140, 22); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#111"; ctx.fillRect(198, 395-bob, 116, 18);
  ctx.fillStyle = "#facc15"; ctx.fillRect(242, 393-bob, 28, 22);

  ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#111"; ctx.lineWidth = 11;
  ctx.beginPath(); ctx.arc(256, 200-bob, 86, 0, Math.PI*2); ctx.fill(); ctx.stroke();

  ctx.fillStyle = "#111";
  if (blink) {
    ctx.lineWidth = 7;
    ctx.beginPath(); ctx.moveTo(212,188-bob); ctx.lineTo(238,188-bob); ctx.moveTo(274,188-bob); ctx.lineTo(300,188-bob); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.arc(225, 186-bob, 10, 0, Math.PI*2); ctx.arc(287, 186-bob, 10, 0, Math.PI*2); ctx.fill();
  }

  ctx.lineWidth = 8;
  const browTilt = CFG.emotion === "determined" ? 8 : (CFG.emotion === "sad" ? -8 : 0);
  ctx.beginPath(); ctx.moveTo(206, 162-bob-browTilt); ctx.lineTo(242, 166-bob+browTilt); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(270, 166-bob+browTilt); ctx.lineTo(306, 162-bob-browTilt); ctx.stroke();

  ctx.fillStyle = "#7f1d1d"; ctx.strokeStyle = "#111"; ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.ellipse(256, 238-bob, 24, 6 + talk * 16, 0, 0, Math.PI*2);
  ctx.fill(); ctx.stroke();

  if (CFG.hat === "tophat") {
    ctx.fillStyle = "#1e293b"; ctx.strokeStyle = "#111"; ctx.lineWidth = 9;
    ctx.beginPath(); ctx.roundRect(160, 118-bob, 192, 22, 10); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.roundRect(192, 42-bob, 128, 80, 10); ctx.fill(); ctx.stroke();
  } else if (CFG.hat === "cap") {
    ctx.fillStyle = "#1d4ed8"; ctx.strokeStyle = "#111"; ctx.lineWidth = 9;
    ctx.beginPath(); ctx.arc(256, 140-bob, 82, Math.PI, 0); ctx.fill(); ctx.stroke();
    ctx.fillRect(240, 130-bob, 115, 16);
  } else if (CFG.hat === "crown") {
    ctx.fillStyle = "#facc15"; ctx.strokeStyle = "#111"; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.moveTo(196,125-bob); ctx.lineTo(206,70-bob); ctx.lineTo(236,105-bob);
    ctx.lineTo(256,60-bob); ctx.lineTo(276,105-bob); ctx.lineTo(306,70-bob); ctx.lineTo(316,125-bob); ctx.closePath();
    ctx.fill(); ctx.stroke();
  }

  if (CFG.prop === "newspaper") {
    ctx.fillStyle = "#fef3c7"; ctx.strokeStyle = "#111"; ctx.lineWidth = 7;
    ctx.fillRect(156, 330-bob, 200, 150); ctx.strokeRect(156, 330-bob, 200, 150);
    ctx.fillStyle = "#111"; ctx.font = "900 22px Arial"; ctx.textAlign = "center";
    ctx.fillText((CFG.headline || "BREAKING NEWS").slice(0,18), 256, 375-bob);
  } else if (CFG.prop === "ice_block") {
    ctx.fillStyle = "rgba(125,211,252,0.85)"; ctx.strokeStyle = "#0284c7"; ctx.lineWidth = 7;
    ctx.fillRect(340, 340-bob, 75, 75); ctx.strokeRect(340, 340-bob, 75, 75);
  } else if (CFG.prop === "gold_coin") {
    ctx.fillStyle = "#facc15"; ctx.strokeStyle = "#111"; ctx.lineWidth = 7;
    ctx.beginPath(); ctx.arc(370, 355-bob, 32, 0, Math.PI*2); ctx.fill(); ctx.stroke();
  }
  tex.needsUpdate = true;
}

const words = CFG.narration.split(/\s+/).filter(Boolean);
window.renderAt = (t, d) => {
  const p = Math.min(1, t / Math.max(0.1, d));
  drawChar(t, d);

  if (CFG.camera_move === "orbit_left") {
    camera.position.set(-2.5 + p * 3.5, 2.4, 7.5 - p * 1.2);
  } else if (CFG.camera_move === "orbit_right") {
    camera.position.set(2.5 - p * 3.5, 2.4, 7.5 - p * 1.2);
  } else if (CFG.camera_move === "closeup") {
    camera.position.set(0, 2.2, 5.2 - p * 1.6);
  } else if (CFG.camera_move === "pan_up") {
    camera.position.set(0, 1.2 + p * 2.2, 7.2);
  } else {
    camera.position.set(0, 2.3, 8.2 - p * 2.4);
  }
  camera.lookAt(0, 1.9, 0.5);
  if (CFG.action === "walk") charMesh.position.x = -1.2 + p * 2.4;

  if (SHOW_CAP) {
    const wi = Math.min(words.length - 1, Math.floor(p * words.length));
    const start = Math.max(0, wi - 1);
    const chunk = words.slice(start, start + 3).map((w, idx) =>
      (start + idx === wi) ? `<span class='hi'>${w}</span>` : w
    ).join(" ");
    document.getElementById("cap").innerHTML = chunk;
  }

  renderer.render(scene, camera);
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
print(f"Generated {len(story_scenes)} ({vtype}) 3D+2D scenes for: {topic}")
