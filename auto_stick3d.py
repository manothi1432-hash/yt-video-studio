import os
import re
import json
import wave
import time
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

topic = os.environ["TOPIC"].strip()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]

def ask_gemini(prompt: str, as_json: bool = False) -> str:
    cfg = types.GenerateContentConfig(response_mime_type="application/json") if as_json else None
    last_err = None
    for m in MODELS:
        for _ in range(2):
            try:
                r = client.models.generate_content(model=m, contents=prompt, config=cfg)
                return r.text
            except Exception as e:
                last_err = e
                print(f"{m} retry: {e}")
                time.sleep(3)
    raise RuntimeError(f"Gemini failed: {last_err}")

def clean_tsx(code: str) -> str:
    return re.sub(r"<Stars\b[^>]*/?>", "", code)

pkg = next(Path(".").rglob("engine/package.json"))
eng_dir = pkg.parent.resolve()
pack_root = eng_dir.parent.resolve()
prep_script = next(pack_root.rglob("prep_voice.py")).resolve()
pub_dir = eng_dir / "public"
pub_dir.mkdir(parents=True, exist_ok=True)

script_text = ask_gemini(
    f'Write a gripping 12-sentence US English YouTube Shorts voiceover script (around 850 to 950 characters total for a 60-second video, spell out ALL numbers in words like "two hundred" with ZERO digits 0-9, ZERO $/% symbols, plain text only) about: "{topic}"'
).strip().strip('"')
if re.search(r"[0-9$%]", script_text):
    script_text = ask_gemini(f"Rewrite spelling out every number and symbol in English words only, no digits:\n{script_text}").strip().strip('"')

script_file = (pack_root / "custom_script.txt").resolve()
script_file.write_text(script_text, encoding="utf-8")
print("Script:", script_text)

mp3_raw = (pack_root / "voice_raw.mp3").resolve()
wav_raw = (pack_root / "voice_raw.wav").resolve()

tts_ok = False
for v in ["en-US-AndrewNeural", "en-US-GuyNeural", "en-US-ChristopherNeural", "en-US-BrianNeural"]:
    try:
        subprocess.run(["edge-tts", "--voice", v, "--text", script_text, "--write-media", str(mp3_raw)], check=True)
        if mp3_raw.exists() and mp3_raw.stat().st_size > 1000:
            tts_ok = True
            print("TTS success with:", v)
            break
    except Exception as e:
        print(f"edge-tts {v} failed: {e}")
        time.sleep(2)

if not tts_ok:
    from gtts import gTTS
    gTTS(text=script_text, lang="en", tld="com").save(str(mp3_raw))

subprocess.run(["ffmpeg", "-y", "-i", str(mp3_raw), "-ar", "16000", "-ac", "1", str(wav_raw)], check=True)

prep_res = subprocess.run(["python3", str(prep_script), str(wav_raw), str(script_file)], cwd=str(pack_root))
if prep_res.returncode != 0 or not (pub_dir / "words.json").exists():
    print("prep_voice skipped unknown brand words; building exact timing fallback...")
    with wave.open(str(wav_raw), "rb") as wf:
        dur = wf.getnframes() / float(wf.getframerate())
    (pub_dir / "voice.wav").write_bytes(wav_raw.read_bytes())
    w_list = script_text.split()
    step = dur / max(1, len(w_list))
    words_data = [{"word": w, "start": round(i * step, 3), "end": round((i + 1) * step, 3)} for i, w in enumerate(w_list)]
    (pub_dir / "words.json").write_text(json.dumps(words_data, indent=2), encoding="utf-8")
    (pub_dir / "script.json").write_text(json.dumps({"text": script_text, "duration": round(dur, 3)}, indent=2), encoding="utf-8")

voice_wav = pub_dir / "voice.wav"
mix_wav = pub_dir / "mix.wav"
if voice_wav.exists() and not mix_wav.exists():
    mix_wav.write_bytes(voice_wav.read_bytes())

def read_opt(rel):
    p = eng_dir / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""

words_json = read_opt("public/words.json")
nvidia_v4 = read_opt("src/videos/NvidiaV4.tsx")
kit_tsx = read_opt("src/style/kit.tsx")
extra_tsx = read_opt("src/style/extra.tsx")
props_tsx = read_opt("src/style/props.tsx")
root_tsx = read_opt("src/Root.tsx")

code_prompt = f"""You are a Remotion + Three.js developer working inside this exact codebase.
Create a complete 10-scene (60-second) vertical 9:16 (720x1280, 30fps) video component `CustomVideo` in `src/videos/CustomVideo.tsx` for the topic: "{topic}".
Alternate different 3D rooms, camera angles, props, and character expressions from NvidiaV4.tsx every 5-6 seconds.

Script:
{script_text}

Word timings (`public/words.json`):
{words_json[:15000]}

Reference working video (`src/videos/NvidiaV4.tsx`):
{nvidia_v4[:9000]}

Helpers (`src/style/kit.tsx`):
{kit_tsx[:5000]}

Extra helpers (`src/style/extra.tsx`):
{extra_tsx[:5000]}

Props (`src/style/props.tsx`):
{props_tsx[:4000]}

Current `src/Root.tsx`:
{root_tsx}

Return ONLY valid JSON with two keys:
{{
  "custom_video_tsx": "full TypeScript code for src/videos/CustomVideo.tsx exporting CustomVideo",
  "root_tsx": "updated src/Root.tsx registering Composition id='CustomVideo' with the exact total durationInFrames matching words.json end time * 30"
}}
CRITICAL: Use ONLY imports and exact prop signatures from NvidiaV4.tsx, kit.tsx, extra.tsx, props.tsx. NEVER use <Stars> anywhere. Never pass undefined props. Include <Audio src={{staticFile("mix.wav")}} />."""

gen = json.loads(ask_gemini(code_prompt, as_json=True))
custom_path = eng_dir / "src/videos/CustomVideo.tsx"
custom_path.parent.mkdir(parents=True, exist_ok=True)
custom_path.write_text(clean_tsx(gen["custom_video_tsx"]), encoding="utf-8")
(eng_dir / "src/Root.tsx").write_text(gen["root_tsx"], encoding="utf-8")

gl = (pack_root / ".gl-flag").read_text().strip() if (pack_root / ".gl-flag").exists() else "swangle"
out_mp4 = Path("remotion_video.mp4").resolve()

for attempt in range(2):
    res = subprocess.run(
        ["npx", "remotion", "render", "CustomVideo", str(out_mp4), f"--gl={gl}", "--concurrency=4", "--log=error"],
        cwd=str(eng_dir), capture_output=True, text=True
    )
    if res.returncode == 0 and out_mp4.exists():
        print("SUCCESS: remotion_video.mp4 ready!")
        raise SystemExit(0)
    print(f"Render attempt {attempt+1} failed:\n{res.stderr[-2500:]}")
    if attempt == 0:
        fix = json.loads(ask_gemini(
            f"Fix the TypeScript/Remotion error in `CustomVideo.tsx` or `Root.tsx` (NEVER use <Stars>):\n{res.stderr[-2500:]}\n\n"
            f"extra.tsx:\n{extra_tsx[:4000]}\n\n"
            f"CustomVideo.tsx:\n{custom_path.read_text()}\n\nRoot.tsx:\n{(eng_dir / 'src/Root.tsx').read_text()}\n\n"
            'Return ONLY JSON: {"custom_video_tsx": "...", "root_tsx": "..."}',
            as_json=True
        ))
        custom_path.write_text(clean_tsx(fix["custom_video_tsx"]), encoding="utf-8")
        (eng_dir / "src/Root.tsx").write_text(fix["root_tsx"], encoding="utf-8")

raise RuntimeError("Remotion render failed after retry")
