
import os
import json
import time
from pathlib import Path
from google import genai
from google.genai import types

items = os.environ.get("ITEMS", "Soda Can, Glass Cube, Bowling Ball, Nokia 3310").strip()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = f"""You are a viral Hydraulic Press YouTube Shorts scriptwriter.
Create 5 exciting scenes testing these items under a hydraulic press: "{items}"
(Scene 1 = quick hook, Scenes 2-5 = each item tested one by one, ending with the hardest/unbreakable one!)

Return ONLY valid JSON:
{{
  "scenes": [
    {{
      "narration": "Short energetic US English line under 130 chars.",
      "item_name": "NOKIA 3310",
      "shape": "phone",
      "color": "#1e3a8a",
      "outcome": "survive",
      "max_tons": 150
    }}
  ]
}}

Allowed values:
- shape: "can", "cube", "sphere", "diamond", "phone", "egg"
- outcome: "crush" (squashes flat), "shatter" (explodes into shards), "survive" (unbreakable!)
- max_tons: integer between 5 and 200"""

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
  body { margin:0; overflow:hidden; background:#090d16; font-family:'Arial Black', Impact, sans-serif; color:#fff; }
  #hud-top { position:fixed; top:6%; left:50%; transform:translateX(-50%); text-align:center; width:90%; pointer-events:none; }
  #vs { font-size:38px; color:#facc15; text-shadow:0 4px 0 #000, -2px -2px 0 #000, 2px 2px 0 #000; letter-spacing:1px; }
  #tons { font-size:66px; color:#ffffff; text-shadow:0 5px 0 #000, -3px -3px 0 #000, 3px 3px 0 #000; margin-top:6px; }
  #stamp { position:fixed; top:26%; left:50%; transform:translate(-50%,-50%) rotate(-6deg) scale(0);
           font-size:56px; padding:10px 26px; border:6px solid #fff; border-radius:14px;
           text-shadow:0 4px 0 #000; box-shadow:0 10px 25px rgba(0,0,0,0.6); pointer-events:none; }
  #cap { position:fixed; left:50%; top:78%; transform:translate(-50%,-50%); text-align:center;
         font-size:46px; font-weight:900; width:88%; line-height:1.12;
         text-shadow:0 4px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000; }
  .hi { color:#facc15; transform:scale(1.15); display:inline-block; }
</style>
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
</head><body>
<div id="hud-top"><div id="vs"></div><div id="tons">0.0 TONS</div></div>
<div id="stamp"></div>
<div id="cap"></div>
<script>
const CFG = __CFG__;
const W = 720, H = 1280;
document.getElementById("vs").textContent = "VS " + (CFG.item_name || "OBJECT").toUpperCase();

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f172a);
scene.fog = new THREE.Fog(0x0f172a, 10, 28);

const camera = new THREE.PerspectiveCamera(45, W/H, 0.1, 60);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(W, H);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const spot = new THREE.SpotLight(0xfffbeb, 2.2);
spot.position.set(4, 10, 6);
spot.castShadow = true;
scene.add(spot);
const rim = new THREE.DirectionalLight(0x38bdf8, 0.9);
rim.position.set(-5, 4, -4);
scene.add(rim);

// Workshop Floor & Anvil Base
const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshStandardMaterial({color:0x1e293b, roughness:0.6}));
floor.rotation.x = -Math.PI/2; floor.receiveShadow = true; scene.add(floor);

const steelMat = new THREE.MeshStandardMaterial({color:0x94a3b8, metalness:0.85, roughness:0.25});
const frameMat = new THREE.MeshStandardMaterial({color:0xdc2626, metalness:0.4, roughness:0.4});
const chromeMat = new THREE.MeshStandardMaterial({color:0xe2e8f0, metalness:0.95, roughness:0.1});

// Heavy Anvil & H-Frame
const anvil = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.8, 2.6), steelMat);
anvil.position.set(0, 0.4, 0); anvil.receiveShadow = true; scene.add(anvil);

[-2.2, 2.2].forEach(x => {
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.45, 7.5, 0.6), frameMat);
  post.position.set(x, 3.75, 0); post.castShadow = true; scene.add(post);
});
const topBeam = new THREE.Mesh(new THREE.BoxGeometry(5.0, 0.7, 0.9), frameMat);
topBeam.position.set(0, 7.2, 0); scene.add(topBeam);

// Moving Hydraulic Piston + Plate
const pressGroup = new THREE.Group();
const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 4.5, 24), chromeMat);
rod.position.set(0, 2.5, 0); pressGroup.add(rod);
const plate = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.45, 2.2), steelMat);
plate.position.set(0, 0.22, 0); plate.castShadow = true; pressGroup.add(plate);
scene.add(pressGroup);

// Target Object
let objGeo;
const sh = CFG.shape || "cube";
if (sh === "can") objGeo = new THREE.CylinderGeometry(0.55, 0.55, 1.4, 24);
else if (sh === "sphere") objGeo = new THREE.SphereGeometry(0.75, 24, 24);
else if (sh === "diamond") objGeo = new THREE.OctahedronGeometry(0.8, 0);
else if (sh === "phone") objGeo = new THREE.BoxGeometry(0.85, 1.5, 0.25);
else if (sh === "egg") { objGeo = new THREE.SphereGeometry(0.65, 20, 20); objGeo.scale(0.8, 1.25, 0.8); }
else objGeo = new THREE.BoxGeometry(1.2, 1.2, 1.2);

const objMat = new THREE.MeshStandardMaterial({
  color: CFG.color || "#38bdf8",
  metalness: (sh === "diamond" || sh === "can") ? 0.6 : 0.2,
  roughness: sh === "diamond" ? 0.05 : 0.3,
  transparent: sh === "diamond",
  opacity: sh === "diamond" ? 0.85 : 1.0
});
const target = new THREE.Mesh(objGeo, objMat);
target.castShadow = true;
const baseHeight = sh === "phone" ? 1.5 : (sh === "can" ? 1.4 : (sh === "sphere" || sh === "diamond" ? 1.5 : 1.2));
target.position.set(0, 0.8 + baseHeight/2, 0);
scene.add(target);

// Explosion Shards / Sparks
const shards = [];
for (let i=0; i<28; i++) {
  const sm = new THREE.Mesh(
    new THREE.TetrahedronGeometry(0.16),
    new THREE.MeshStandardMaterial({color: CFG.outcome==="survive" ? 0xfacc15 : (CFG.color || "#38bdf8"), emissive: CFG.outcome==="survive"?0xf97316:0x000000})
  );
  sm.visible = false;
  sm.userData = { vx: Math.sin(i*13)*4.5, vy: 2.0 + (i%5)*1.2, vz: Math.cos(i*17)*4.5 };
  scene.add(sm); shards.push(sm);
}

const WORDS = CFG.narration.split(/\s+/).filter(Boolean);
window.renderAt = (t, d) => {
  const p = Math.min(1, t / Math.max(0.1, d));
  const impactT = 0.45;
  const maxTons = CFG.max_tons || 100;

  // Piston Descent
  let plateY = 4.2;
  let tons = 0;
  let shake = 0;

  if (p < impactT) {
    const ap = p / impactT;
    plateY = 4.2 - ap * (4.2 - (0.8 + baseHeight));
    tons = ap * 5;
  } else {
    const cp = Math.min(1, (p - impactT) / 0.40);
    tons = 5 + cp * (maxTons - 5);

    if (CFG.outcome === "crush") {
      const sy = Math.max(0.14, 1 - cp * 0.86);
      const sxz = 1 + cp * 0.48;
      target.scale.set(sxz, sy, sxz);
      target.position.y = 0.8 + (baseHeight * sy) / 2;
      plateY = 0.8 + baseHeight * sy;
      shake = cp < 0.8 ? 0.14 : 0;
    } else if (CFG.outcome === "shatter") {
      if (cp < 0.25) {
        plateY = 0.8 + baseHeight;
        target.scale.set(1 + cp*0.1, 1 - cp*0.15, 1 + cp*0.1);
      } else {
        target.visible = false;
        plateY = 0.8 + baseHeight - (cp - 0.25) * 1.1;
        const ft = (cp - 0.25) * 1.6;
        shards.forEach(s => {
          s.visible = true;
          s.position.set(s.userData.vx*ft, 1.3 + s.userData.vy*ft - 4.5*ft*ft, s.userData.vz*ft);
          s.rotation.set(ft*8, ft*6, 0);
        });
        shake = cp < 0.65 ? 0.22 : 0;
      }
    } else {
      // Survive (unbreakable!)
      plateY = 0.8 + baseHeight;
      shake = Math.sin(t*60) * 0.08;
      const ft = cp * 1.4;
      shards.forEach(s => {
        s.visible = true;
        s.position.set(s.userData.vx*ft*0.8, 1.6 + s.userData.vy*ft*0.6 - 4.0*ft*ft, s.userData.vz*ft*0.8);
      });
    }
  }

  pressGroup.position.y = plateY;
  const tonsEl = document.getElementById("tons");
  tonsEl.textContent = tons.toFixed(1) + " TONS";
  tonsEl.style.color = tons > maxTons*0.7 ? "#ef4444" : (tons > maxTons*0.35 ? "#f97316" : "#ffffff");

  // Result Stamp
  const st = document.getElementById("stamp");
  if (p > 0.72) {
    const label = CFG.outcome === "survive" ? "UNBREAKABLE!" : (CFG.outcome === "shatter" ? "SHATTERED!" : "CRUSHED!");
    const col = CFG.outcome === "survive" ? "#22c55e" : "#ef4444";
    st.textContent = label;
    st.style.color = col; st.style.borderColor = col;
    st.style.transform = "translate(-50%,-50%) rotate(-6deg) scale(1)";
  } else {
    st.style.transform = "translate(-50%,-50%) rotate(-6deg) scale(0)";
  }

  // Dynamic Camera + Shake
  const sx = (Math.sin(t*50)*shake), sy = (Math.cos(t*57)*shake);
  camera.position.set(sx + Math.sin(p*1.5)*0.8, 2.8 - p*0.4 + sy, 6.8 - p*1.4);
  camera.lookAt(0, 1.7, 0);

  // Word-by-Word Pop Captions
  if (WORDS.length) {
    const wi = Math.min(WORDS.length - 1, Math.floor(p * WORDS.length));
    const start = Math.max(0, wi - 1);
    document.getElementById("cap").innerHTML = WORDS.slice(start, start + 3)
      .map((w, i) => (start + i === wi) ? `<span class='hi'>${w}</span>` : w).join(" ");
  }

  renderer.render(scene, camera);
};
renderAt(0, 4);
</script></body></html>"""

story_scenes = []
for sc in plan["scenes"]:
    story_scenes.append({
        "narration": sc["narration"],
        "html": HTML_TEMPLATE.replace("__CFG__", json.dumps(sc))
    })

out = {"width": 720, "height": 1280, "voice": "en-US-BrianMultilingualNeural", "scenes": story_scenes}
Path("story.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Generated {len(story_scenes)} 3D Hydraulic Press scenes for: {items}")
