import os
import re
import json
import time
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

topic = os.environ["TOPIC"].strip()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]

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
                time.sleep(4)
    raise RuntimeError(f"Gemini failed: {last_err}")

pkg = next(Path(".").rglob("engine/package.json"))
eng_dir = pkg.parent.resolve()
pack_root = eng_dir.parent.resolve()
prep_script = next(pack_root.rglob("prep_voice.py")).resolve()
pub_dir = eng_dir / "public"
pub_dir.mkdir(parents=True, exist_ok=True)

script_text = ask_gemini(
    f'Write a punchy 5-sentence US English YouTube Shorts voiceover script (max 350 chars, spell out ALL numbers in words like "two hundred" with ZERO digits 0-9, ZERO $/% symbols, and NO hyphenated words, plain text only) about: "{topic}"'
).strip().strip('"')
# Extra safety: ask Gemini to spell out any remaining digits if present
if re.search(r"[0-9$%]", script_text):
    script_text = ask_gemini(f"Rewrite this text spelling out every number and symbol in plain English words only, no digits:\n{script_text}").strip().strip('"')

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
subprocess.run(["python3", str(prep_script), str(wav_raw), str(script_file)], cwd=str(pack_root), check=True)

voice_wav = pub_dir / "voice.wav"
mix_wav = pub_dir / "mix.wav"
if voice_wav.exists() and not mix_wav.exists():
    mix_wav.write_bytes(voice_wav.read_bytes())

words_json = (pub_dir / "words.json").read_text(encoding="utf-8")
nvidia_v4 = (eng_dir / "src/videos/NvidiaV4.tsx").read_text(encoding="utf-8") if (eng_dir / "src/videos/NvidiaV4.tsx").exists() else ""
kit_tsx = (eng_dir / "src/style/kit.tsx").read_text(encoding="utf-8") if (eng_dir / "src/style/kit.tsx").exists() else ""
root_tsx = (eng_dir / "src/Root.tsx").read_text(encoding="utf-8")

code_prompt = f"""You are a Remotion + Three.js developer working inside this exact codebase.
Create a complete 5-scene vertical 9:16 (720x1280, 30fps) video component `CustomVideo` in `src/videos/CustomVideo.tsx` for the topic: "{topic}".

Script:
{script_text}

Word timings (`public/words.json`):
{words_json[:6000]}

Reference working video (`src/videos/NvidiaV4.tsx`):
{nvidia_v4[:9000]}

Available helper components (`src/style/kit.tsx`):
{kit_tsx[:6000]}

Current `src/Root.tsx`:
{root_tsx}

Return ONLY valid JSON with two keys:
{{
  "custom_video_tsx": "full TypeScript code for src/videos/CustomVideo.tsx exporting CustomVideo",
  "root_tsx": "updated src/Root.tsx registering Composition id='CustomVideo' with the exact total durationInFrames matching words.json end time * 30"
}}
Use ONLY imports and props that exist in NvidiaV4.tsx and kit.tsx. Include <Audio src={{staticFile("mix.wav")}} />."""

gen = json.loads(ask_gemini(code_prompt, as_json=True))
custom_path = eng_dir / "src/videos/CustomVideo.tsx"
custom_path.parent.mkdir(parents=True, exist_ok=True)
custom_path.write_text(gen["custom_video_tsx"], encoding="utf-8")
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
            f"Fix the TypeScript/Remotion error in `CustomVideo.tsx` or `Root.tsx`:\n{res.stderr[-2500:]}\n\n"
            f"CustomVideo.tsx:\n{custom_path.read_text()}\n\nRoot.tsx:\n{(eng_dir / 'src/Root.tsx').read_text()}\n\n"
            'Return ONLY JSON: {"custom_video_tsx": "...", "root_tsx": "..."}',
            as_json=True
        ))
        custom_path.write_text(fix["custom_video_tsx"], encoding="utf-8")
        (eng_dir / "src/Root.tsx").write_text(fix["root_tsx"], encoding="utf-8")

raise RuntimeError("Remotion render failed after retry")
