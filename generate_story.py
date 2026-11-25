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

prompt = f"""You are a viral YouTube video director (RicksClips / Neon-Rush-3D style).
Break this topic into {scene_count} vivid scenes: "{topic}"

Return ONLY valid JSON with this exact schema:
{{
  "scenes": [
    {{
      "narration": "{length_hint}",
      "setting": "ocean_ship",
      "sky": "day",
      "camera_move": "orbit_left",
      "hat": "tophat",
      "shirt_color": "#b91c1c",
      "emotion": "determined",
      "action": "walk",
      "prop": "ice_block",
      "headline": "A SHIP FULL OF ICE?!",
      "stat_text": "",
      "has_buddy": false
    }}
  ]
}}

Allowed values:
- setting: "ocean_ship", "town_bridge", "ice_pond", "city_street", "forest_camp", "office_room", "earth_space"
- sky: "day", "sunset", "night"
- camera_move: "dolly_in", "orbit_left", "orbit_right", "closeup", "pan_up", "low_hero"
- hat: "tophat", "cap", "crown", "none"
- emotion: "happy", "shocked", "smug", "determined", "sad"
- action: "walk", "wave", "point", "talk"
- prop: "ice_block", "newspaper", "gold_coin", "map", "none"
- headline: short 2-4 word text if prop is newspaper, else ""
- stat_text: optional bold 1-3 word number/fact at top (e.g. "1806", "8.7 MILLION") for key scenes, else ""
- has_buddy: true or false (add a 2nd reacting stick-figure character)"""

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
  #stat { position:fixed; left:50%; top:12%; transform:translate(-50%,-50%); text-align:center;
          font-size:58px; font-weight:900; color:#facc15; letter-spacing:2px;
          text-shadow: 0 5px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000;
          pointer-events:none; width:90%; }
  #cap { position:fixed; left:50%; top:62%; transform:translate(-50%,-50%); text-align:center;
         font-size:48px; font-weight:900; color:#fff;
         text-shadow: 0 4px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000;
         pointer-events:none; width:88%; line-height:1.12; }
  .hi { color:#facc15; transform:scale(1.14); display:inline-block; }
</style>
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
</head><body>
<div id="stat"></div>
<div id="cap"></div>
<script>
const CFG = __CFG__;
const W = __W__, H = __H__;
const SHOW_CAP = __SHOW_CAP__;
if (!SHOW_CAP) document.getElementById("cap").style.display = "none";
if (CFG.stat_text) document.getElementById("stat").textContent = CFG.stat_text;

const scene = new THREE.Scene();
const skyColors = { day: 0x56b4f9, sunset: 0xf97316, night: 0x0b1120 };
const isSpace = (CFG.setting === "earth_space");
scene.background = new THREE.Color(isSpace ? 0x050816 : (skyColors[CFG.sky] || 0x56b4f9));
scene.fog = new THREE.Fog(scene.background, 16, 58);

const camera = new THREE.PerspectiveCamera(46, W/H, 0.1, 120);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.8));
const sun = new THREE.DirectionalLight(CFG.sky === "sunset" ? 0xfdba74 : 0xfffbeb, 1.35);
sun.position.set(10, 16, 12);
sun.castShadow = true;
scene.add(sun);

function box(w,h,d,col,x,y,z,ry=0,em=0x000000){
  const m = new THREE.Mesh(new THREE.BoxGeometry(w,h,d), new THREE.MeshStandardMaterial({color:col, emissive:em, roughness:0.7}));
  m.position.set(x,y,z); m.rotation.y=ry; m.castShadow=true; m.receiveShadow=true; scene.add(m); return m;
}
function cyl(rt,rb,h,col,x,y,z,rz=0){
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt,rb,h,14), new THREE.MeshStandardMaterial({color:col, roughness:0.75}));
  m.position.set(x,y,z); m.rotation.z=rz; m.castShadow=true; scene.add(m); return m;
}
function sph(r,col,x,y,z,em=0x000000){
  const m = new THREE.Mesh(new THREE.SphereGeometry(r,16,12), new THREE.MeshStandardMaterial({color:col, emissive:em, roughness:0.6}));
  m.position.set(x,y,z); m.castShadow=true; scene.add(m); return m;
}

// Sky Sun/Moon & Drifting Clouds
const clouds = [];
if (!isSpace) {
  sph(1.8, CFG.sky==="night" ? 0xe2e8f0 : 0xfef08a, -9, 12, -28, CFG.sky==="night" ? 0x94a3b8 : 0xfacc15);
  for (let i=0; i<5; i++) {
    const g = new THREE.Group();
    const cx = -14 + i*7, cy = 8 + (i%2)*2, cz = -20 - (i%3)*4;
    [[-1,0,0,1.1],[0,0.4,0,1.4],[1.1,0,0,1.0]].forEach(([ox,oy,oz,r])=>{
      const cm = new THREE.Mesh(new THREE.SphereGeometry(r,10,8), new THREE.MeshBasicMaterial({color: CFG.sky==="night"?0x334155:0xffffff}));
      cm.position.set(ox,oy,oz); g.add(cm);
    });
    g.position.set(cx,cy,cz); scene.add(g); clouds.push(g);
  }
  // Distant Rolling Hills
  for (let i=-3; i<=3; i++) sph(5.5, 0x3f6212, i*6, -2.5, -24);
}

// Ground / Animated Water
const isWater = (CFG.setting === "ocean_ship" || CFG.setting === "town_bridge");
let ground = null, groundPos = null;
if (!isSpace) {
  const groundGeo = new THREE.PlaneGeometry(90, 90, 28, 28);
  const groundMat = new THREE.MeshStandardMaterial({
    color: isWater ? 0x0284c7 : 0x4d7c0f,
    roughness: isWater ? 0.15 : 0.92,
    metalness: isWater ? 0.25 : 0.0
  });
  ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);
  groundPos = groundGeo.attributes.position;
}

// Detailed 3D Environments
let earthGlobe = null;
if (CFG.setting === "ocean_ship") {
  box(4.8, 0.35, 11, 0x78350f, 0, 0.35, 1.5); // dock deck
  for(let z=-3; z<=5; z+=2){ cyl(0.15,0.15,1.2,0x451a03,-2.1,0.1,z); cyl(0.15,0.15,1.2,0x451a03,2.1,0.1,z); }
  // Ship
  box(5.5, 2.0, 12, 0x451a03, 0, 1.0, -7.5, 0.18);
  box(5.7, 0.4, 12.2, 0x78350f, 0, 2.1, -7.5, 0.18);
  cyl(0.16, 0.2, 8.5, 0x78350f, 0, 5.5, -7.5);
  box(4.2, 3.4, 0.12, 0xfef3c7, 0, 6.2, -7.1, 0.18);
  // Palm tree + ice crates
  cyl(0.18, 0.28, 4.5, 0x78350f, 2.0, 2.4, 2.5, -0.15);
  for(let a=0;a<5;a++){ box(1.8,0.12,0.5,0x15803d, 2.4+Math.cos(a)*0.8, 4.6, 2.5+Math.sin(a)*0.8, a); }
  box(1.1, 1.1, 1.1, 0xbae6fd, -1.4, 1.05, 1.8);
  box(0.9, 0.9, 0.9, 0x7dd3fc, -1.4, 2.0, 1.8, 0.3);
} else if (CFG.setting === "town_bridge") {
  box(16, 0.45, 3.4, 0x78350f, 0, 0.85, 0);
  box(16, 0.15, 0.15, 0x451a03, 0, 1.75, 1.6);
  box(16, 0.15, 0.15, 0x451a03, 0, 1.75, -1.6);
  for(let x=-6;x<=6;x+=3){ cyl(0.08,0.08,1.0,0x451a03,x,1.3,1.6); cyl(0.08,0.08,1.0,0x451a03,x,1.3,-1.6); }
  box(5, 3.8, 4, 0xe7e5e4, -5.5, 1.9, -6);
  box(5.6, 1.8, 4.6, 0x991b1b, -5.5, 4.6, -6);
  box(1.1, 1.2, 0.1, 0xfef08a, -5.5, 2.2, -3.95, 0, 0xfacc15); // glowing window
  box(5, 4.4, 4, 0xfef3c7, 5.5, 2.2, -6.5);
  box(5.6, 1.8, 4.6, 0x1e3a8a, 5.5, 5.2, -6.5);
  box(1.1, 1.2, 0.1, 0xfef08a, 5.5, 2.4, -4.45, 0, 0xfacc15);
} else if (CFG.setting === "ice_pond") {
  box(16, 0.18, 16, 0xbae6fd, 0, 0.08, 0);
  for(let i=-2;i<=2;i++) box(1.3, 1.3, 1.3, 0x7dd3fc, i*1.7, 0.75, -3.2);
  for(let i=-1;i<=1;i++) box(1.3, 1.3, 1.3, 0x38bdf8, i*1.7, 2.05, -3.2);
  for(let x of [-5,5]){ cyl(0.2,0.28,2.2,0x78350f,x,1.1,-5); box(2.2,2.8,2.2,0x166534,x,3.1,-5); box(1.8,0.5,1.8,0xf8fafc,x,4.6,-5); }
} else if (CFG.setting === "city_street") {
  box(50, 0.12, 6, 0x1e293b, 0, 0.07, 0);
  box(50, 0.14, 0.25, 0xfacc15, 0, 0.08, 0);
  [[-6,10,-7,0x475569],[0,8,-9,0x64748b],[6,13,-7,0x334155]].forEach(([bx,bh,bz,bc])=>{
    box(4.5, bh, 4.5, bc, bx, bh/2, bz);
    for(let wy=2; wy<bh-1; wy+=2) for(let wx=-1; wx<=1; wx+=2) box(0.8,0.9,0.1,0xfef08a, bx+wx, wy, bz+2.26, 0, 0xfacc15);
  });
} else if (CFG.setting === "office_room") {
  box(18, 9, 0.3, 0xf1f5f9, 0, 4.5, -5);
  box(3.5, 2.5, 0.15, 0x38bdf8, -4, 4.8, -4.8, 0, 0x0284c7); // window
  box(4.4, 1.3, 2.2, 0x78350f, 0, 0.65, -2.2);
  box(1.8, 1.1, 0.12, 0x0f172a, 0, 1.9, -2.2);
  box(1.6, 0.9, 0.14, 0x38bdf8, 0, 1.9, -2.18, 0, 0x0284c7);
} else if (isSpace) {
  for(let i=0;i<40;i++) sph(0.08, 0xffffff, (Math.sin(i*17)*18), (Math.cos(i*23)*12)+2, -15-(i%10), 0xffffff);
  earthGlobe = new THREE.Group();
  const ocean = new THREE.Mesh(new THREE.SphereGeometry(3.2, 24, 24), new THREE.MeshStandardMaterial({color:0x0284c7, roughness:0.3}));
  earthGlobe.add(ocean);
  const cont1 = new THREE.Mesh(new THREE.SphereGeometry(3.24, 12, 12, 0, 1.5, 0.6, 1.2), new THREE.MeshStandardMaterial({color:0x22c55e}));
  earthGlobe.add(cont1);
  earthGlobe.position.set(0, -1.6, 0.8);
  scene.add(earthGlobe);
} else {
  for(let i=-3;i<=3;i+=2){ cyl(0.22,0.32,2.6,0x78350f,i*2.2,1.3,-4.5); sph(1.5,0x15803d,i*2.2,3.4,-4.5); }
}

function makeCharCanvas(cfg) {
  const c2 = document.createElement("canvas");
  c2.width = 512; c2.height = 640;
  const ctx = c2.getContext("2d");
  const tex = new THREE.CanvasTexture(c2);
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2.7, 3.38), mat);
  return { c2, ctx, tex, mesh };
}

const mainChar = makeCharCanvas(CFG);
mainChar.mesh.position.set(CFG.has_buddy ? -0.9 : 0, 1.85, 1.3);
scene.add(mainChar.mesh);

let buddyChar = null;
if (CFG.has_buddy) {
  buddyChar = makeCharCanvas(CFG);
  buddyChar.mesh.position.set(1.2, 1.85, 1.1);
  scene.add(buddyChar.mesh);
}

function drawPerson(ch, t, cfg, isBuddy=false) {
  const { ctx, tex } = ch;
  ctx.clearRect(0, 0, 512, 640);
  const phase = isBuddy ? 1.7 : 0;
  const bob = Math.abs(Math.sin(t * 7 + phase)) * 10;
  const tilt = Math.sin(t * 4 + phase) * 0.04;
  const talk = isBuddy ? 0.1 : Math.abs(Math.sin(t * 14));
  const blink = (Math.floor((t + phase) * 2.5) % 7 === 0);
  const legSwing = (!isBuddy && cfg.action === "walk") ? Math.sin(t * 7) * 30 : 0;
  const armWave = (!isBuddy && (cfg.action === "wave" || cfg.action === "point")) ? Math.sin(t * 6) * 38 : Math.sin(t * 3 + phase) * 12;

  ctx.save();
  ctx.translate(256, 420);
  ctx.rotate(tilt);
  ctx.translate(-256, -420);
  ctx.lineCap = "round"; ctx.lineJoin = "round";

  ctx.strokeStyle = "#111"; ctx.lineWidth = 14;
  ctx.beginPath(); ctx.moveTo(235, 420-bob); ctx.lineTo(220+legSwing, 570); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(277, 420-bob); ctx.lineTo(292-legSwing, 570); ctx.stroke();

  ctx.beginPath(); ctx.moveTo(205, 315-bob); ctx.lineTo(138, 385-bob-armWave); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(307, 315-bob); ctx.lineTo(374, 375-bob+armWave*0.5); ctx.stroke();

  ctx.fillStyle = isBuddy ? "#1d4ed8" : (cfg.shirt_color || "#b91c1c");
  ctx.strokeStyle = "#111"; ctx.lineWidth = 10;
  ctx.beginPath(); ctx.roundRect(198, 290-bob, 116, 140, 22); ctx.fill(); ctx.stroke();
  ctx.fillStyle = "#111"; ctx.fillRect(198, 395-bob, 116, 18);
  ctx.fillStyle = "#facc15"; ctx.fillRect(242, 393-bob, 28, 22);

  ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#111"; ctx.lineWidth = 11;
  ctx.beginPath(); ctx.arc(256, 200-bob, 86, 0, Math.PI*2); ctx.fill(); ctx.stroke();

  const emo = isBuddy ? "shocked" : cfg.emotion;
  ctx.fillStyle = "#111";
  if (blink) {
    ctx.lineWidth = 7;
    ctx.beginPath(); ctx.moveTo(212,188-bob); ctx.lineTo(238,188-bob); ctx.moveTo(274,188-bob); ctx.lineTo(300,188-bob); ctx.stroke();
  } else if (emo === "smug") {
    ctx.lineWidth = 7;
    ctx.beginPath(); ctx.moveTo(208,182-bob); ctx.lineTo(240,182-bob); ctx.moveTo(272,182-bob); ctx.lineTo(304,182-bob); ctx.stroke();
    ctx.beginPath(); ctx.arc(224, 190-bob, 8, 0, Math.PI); ctx.arc(288, 190-bob, 8, 0, Math.PI); ctx.fill();
  } else {
    const er = emo === "shocked" ? 13 : 10;
    ctx.beginPath(); ctx.arc(225, 186-bob, er, 0, Math.PI*2); ctx.arc(287, 186-bob, er, 0, Math.PI*2); ctx.fill();
  }

  ctx.lineWidth = 8;
  const browTilt = emo === "determined" ? 9 : (emo === "sad" || emo === "shocked" ? -9 : 0);
  ctx.beginPath(); ctx.moveTo(206, 160-bob-browTilt); ctx.lineTo(242, 164-bob+browTilt); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(270, 164-bob+browTilt); ctx.lineTo(306, 160-bob-browTilt); ctx.stroke();

  ctx.fillStyle = "#7f1d1d"; ctx.strokeStyle = "#111"; ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.ellipse(256, 238-bob, emo==="shocked"?18:24, 6 + talk * 16, 0, 0, Math.PI*2);
  ctx.fill(); ctx.stroke();

  const hat = isBuddy ? "cap" : cfg.hat;
  if (hat === "tophat") {
    ctx.fillStyle = "#1e293b"; ctx.strokeStyle = "#111"; ctx.lineWidth = 9;
    ctx.beginPath(); ctx.roundRect(160, 118-bob, 192, 22, 10); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.roundRect(192, 42-bob, 128, 80, 10); ctx.fill(); ctx.stroke();
  } else if (hat === "cap") {
    ctx.fillStyle = "#1d4ed8"; ctx.strokeStyle = "#111"; ctx.lineWidth = 9;
    ctx.beginPath(); ctx.arc(256, 140-bob, 82, Math.PI, 0); ctx.fill(); ctx.stroke();
    ctx.fillRect(240, 130-bob, 115, 16);
  } else if (hat === "crown") {
    ctx.fillStyle = "#facc15"; ctx.strokeStyle = "#111"; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.moveTo(196,125-bob); ctx.lineTo(206,70-bob); ctx.lineTo(236,105-bob);
    ctx.lineTo(256,60-bob); ctx.lineTo(276,105-bob); ctx.lineTo(306,70-bob); ctx.lineTo(316,125-bob); ctx.closePath();
    ctx.fill(); ctx.stroke();
  }

  if (!isBuddy) {
    if (cfg.prop === "newspaper") {
      ctx.fillStyle = "#fef3c7"; ctx.strokeStyle = "#111"; ctx.lineWidth = 7;
      ctx.fillRect(156, 330-bob, 200, 150); ctx.strokeRect(156, 330-bob, 200, 150);
      ctx.fillStyle = "#111"; ctx.font = "900 22px Arial"; ctx.textAlign = "center";
      ctx.fillText((cfg.headline || "BREAKING NEWS").slice(0,18), 256, 375-bob);
    } else if (cfg.prop === "ice_block") {
      ctx.fillStyle = "rgba(125,211,252,0.85)"; ctx.strokeStyle = "#0284c7"; ctx.lineWidth = 7;
      ctx.fillRect(340, 340-bob, 75, 75); ctx.strokeRect(340, 340-bob, 75, 75);
    } else if (cfg.prop === "gold_coin") {
      ctx.fillStyle = "#facc15"; ctx.strokeStyle = "#111"; ctx.lineWidth = 7;
      ctx.beginPath(); ctx.arc(370, 355-bob, 32, 0, Math.PI*2); ctx.fill(); ctx.stroke();
    }
  }
  ctx.restore();
  tex.needsUpdate = true;
}

const words = CFG.narration.split(/\s+/).filter(Boolean);
window.renderAt = (t, d) => {
  const rawP = Math.min(1, t / Math.max(0.1, d));
  const p = rawP * rawP * (3 - 2 * rawP); // Smooth ease-in-out

  clouds.forEach((c, idx) => { c.position.x += Math.sin(t*0.5 + idx) * 0.005; });
  if (isWater && groundPos) {
    for (let i=0; i<groundPos.count; i++) {
      const x = groundPos.getX(i), y = groundPos.getY(i);
      groundPos.setZ(i, Math.sin(x*0.35 + t*3.2) * 0.14 + Math.cos(y*0.3 + t*2.5) * 0.1);
    }
    groundPos.needsUpdate = true;
  }
  if (earthGlobe) earthGlobe.rotation.y = t * 0.35;

  drawPerson(mainChar, t, CFG, false);
  if (buddyChar) drawPerson(buddyChar, t, CFG, true);

  if (CFG.camera_move === "orbit_left") {
    camera.position.set(-3.0 + p * 4.2, 2.5, 7.6 - p * 1.4);
  } else if (CFG.camera_move === "orbit_right") {
    camera.position.set(3.0 - p * 4.2, 2.5, 7.6 - p * 1.4);
  } else if (CFG.camera_move === "closeup") {
    camera.position.set(0, 2.3, 5.4 - p * 1.8);
  } else if (CFG.camera_move === "pan_up") {
    camera.position.set(0, 1.1 + p * 2.4, 7.4);
  } else if (CFG.camera_move === "low_hero") {
    camera.position.set(-0.6 + p * 1.2, 1.1, 6.2 - p * 1.2);
  } else {
    camera.position.set(0, 2.4, 8.4 - p * 2.6);
  }
  camera.lookAt(0, 2.0, 0.5);
  if (CFG.action === "walk" && !CFG.has_buddy) mainChar.mesh.position.x = -1.4 + rawP * 2.8;

  if (SHOW_CAP) {
    const wi = Math.min(words.length - 1, Math.floor(rawP * words.length));
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
print(f"Generated {len(story_scenes)} ({vtype}) upgraded 3D+2D scenes for: {topic}")
