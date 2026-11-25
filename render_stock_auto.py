import os
import json
import math
import time
import wave
import struct
import random
import subprocess
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image
from google import genai
from google.genai import types

topic = os.environ["TOPIC"].strip()
vtype = os.environ.get("VIDEO_TYPE", "short").strip().lower()
is_long = (vtype == "long")
W, H = (1280, 720) if is_long else (720, 1280)
SCENES_N = 12 if is_long else 7
VOICE = "en-US-AndrewMultilingualNeural"

WORK = Path("stock_tmp")
WORK.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "YTVideoStudio/1.0 (educational project)"}

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
prompt = f"""You are a viral USA YouTube documentary director.
Break this topic into {SCENES_N} high-retention scenes: "{topic}"

Return ONLY valid JSON:
{{
  "scenes": [
    {{
      "narration": "{'1-2 dramatic US English sentences (140-220 chars)' if is_long else '1 punchy US English sentence (under 130 chars)'}",
      "search_query": "2-3 word Wikimedia/NASA photo search query in English",
      "key_text": "optional 1-3 word UPPERCASE hook/stat (e.g. NO ESCAPE, 100 MILLION) on important scenes, else empty string"
    }}
  ]
}}"""

MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
resp = None
for m in MODELS:
    for _ in range(2):
        try:
            resp = client.models.generate_content(
                model=m, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            break
        except Exception as e:
            print(f"{m} error: {e}")
            time.sleep(4)
    if resp is not None:
        break
if resp is None:
    raise RuntimeError("All Gemini models failed")

plan = json.loads(resp.text)["scenes"]

def get_dur(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())

def make_sfx(out_wav: Path, has_boom: bool):
    sr = 44100
    dur = 0.75 if has_boom else 0.40
    n = int(sr * dur)
    samples = []
    lp = 0.0
    for i in range(n):
        t = i / sr
        env = math.sin(min(1.0, t / 0.12) * math.pi / 2) * math.exp(-t * 5.5)
        noise = (random.random() * 2 - 1)
        lp = lp * 0.85 + noise * 0.15
        val = lp * env * 0.6
        if has_boom:
            freq = 68.0 - 34.0 * min(1.0, t / 0.5)
            val += math.sin(2 * math.pi * freq * t) * math.exp(-t * 4.2) * 0.85
        s = max(-32767, min(32767, int(val * 32767)))
        samples.append(struct.pack("<h", s))
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"".join(samples))

def ass_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def write_ass(text: str, key_text: str, dur: float, out_path: Path):
    words = text.split()
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,DejaVu Sans,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,300,1
Style: BigKey,DejaVu Sans,64,&H0015CCFA,&H0015CCFA,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,5,3,8,40,40,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    if key_text:
        kt = key_text.strip().upper()
        lines.append(f"Dialogue: 1,0:00:00.00,{ass_time(min(dur, 2.2))},BigKey,,0,0,0,,{kt}")
    if (not is_long) and words:
        step = dur / len(words)
        for i, w in enumerate(words):
            st = ass_time(i * step)
            et = ass_time((i + 1) * step)
            s_idx = max(0, i - 1)
            chunk = " ".join(
                (r"{\c&H0015CCFA&}" + ww + r"{\c&H00FFFFFF&}") if (s_idx + k == i) else ww
                for k, ww in enumerate(words[s_idx:s_idx + 3])
            )
            lines.append(f"Dialogue: 0,{st},{et},Pop,,0,0,0,,{chunk}")
    out_path.write_text(header + "\n".join(lines), encoding="utf-8")

used_urls = set()
def fetch_free_image(query: str, out_jpg: Path):
    for q in (query, topic.split()[0], "earth space"):
        try:
            r = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                headers=HEADERS,
                params={
                    "action": "query", "generator": "search",
                    "gsrsearch": f"{q} filetype:bitmap", "gsrnamespace": 6,
                    "gsrlimit": 6, "prop": "imageinfo", "iiprop": "url|mime",
                    "iiurlwidth": 1400, "format": "json"
                },
                timeout=15,
            )
            pages = r.json().get("query", {}).get("pages", {}).values()
            for pg in pages:
                info = (pg.get("imageinfo") or [{}])[0]
                u = info.get("thumburl") or info.get("url")
                if u and u not in used_urls and ("jpeg" in info.get("mime", "") or "png" in info.get("mime", "")):
                    img = Image.open(BytesIO(requests.get(u, headers=HEADERS, timeout=20).content)).convert("RGB")
                    used_urls.add(u)
                    img.save(out_jpg, quality=92)
                    return
        except Exception as e:
            print(f"Wikimedia retry ({q}): {e}")

        try:
            r = requests.get("https://images-api.nasa.gov/search", params={"q": q, "media_type": "image"}, timeout=15)
            for it in r.json().get("collection", {}).get("items", []):
                u = (it.get("links") or [{}])[0].get("href")
                if u and u not in used_urls:
                    img = Image.open(BytesIO(requests.get(u, timeout=20).content)).convert("RGB")
                    used_urls.add(u)
                    img.save(out_jpg, quality=92)
                    return
        except Exception as e:
            print(f"NASA retry ({q}): {e}")
    raise RuntimeError(f"No image found for {query}")

clips = []
for idx, sc in enumerate(plan, start=1):
    mp3 = WORK / f"a_{idx:02d}.mp3"
    subprocess.run([
        "edge-tts", "--voice", VOICE, "--rate=+14%",
        "--text", sc["narration"], "--write-media", str(mp3)
    ], check=True)
    dur = get_dur(mp3) + 0.08
    frames = max(2, int(dur * 24) + 1)

    raw_jpg = WORK / f"img_{idx:02d}.jpg"
    fetch_free_image(sc["search_query"], raw_jpg)

    sfx_wav = WORK / f"sfx_{idx:02d}.wav"
    key_txt = (sc.get("key_text") or "").strip()
    make_sfx(sfx_wav, has_boom=bool(key_txt))

    # 4 Alternating Camera Motions: Zoom-in, Zoom-out, Pan Left, Pan Right
    m_type = idx % 4
    if m_type == 0:
        zp = f"z='min(1+0.20*on/{frames},1.22)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    elif m_type == 1:
        zp = f"z='max(1.22-0.20*on/{frames},1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    elif m_type == 2:
        zp = f"z='1.18':x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)'"
    else:
        zp = f"z='1.18':x='(iw-iw/zoom)*(on/{frames})':y='ih/2-(ih/zoom/2)'"

    vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
          f"zoompan={zp}:d={frames}:s={W}x{H}:fps=24,setsar=1")

    if (not is_long) or key_txt:
        ass_file = WORK / f"sub_{idx:02d}.ass"
        write_ass(sc["narration"], key_txt, dur, ass_file)
        vf += f",ass={ass_file.as_posix()}"

    clip_mp4 = WORK / f"clip_{idx:02d}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_jpg), "-i", str(mp3), "-i", str(sfx_wav),
        "-vf", vf,
        "-filter_complex", "[1:a]acompressor=threshold=-18dB:ratio=3:attack=5:release=50[vo];[2:a]volume=0.45[fx];[vo][fx]amix=inputs=2:duration=first,loudnorm=I=-14:TP=-1.5:LRA=7[aout]",
        "-map", "0:v", "-map", "[aout]", "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", str(clip_mp4)
    ], check=True)
    clips.append(clip_mp4)
    print(f"Done scene {idx}/{len(plan)}: {sc['search_query']} | key={key_txt} ({dur:.2f}s)")

concat_txt = WORK / "concat.txt"
concat_txt.write_text("\n".join(f"file '{c.resolve()}'" for c in clips), encoding="utf-8")
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
    "-c", "copy", "-movflags", "+faststart", "stock_video.mp4"
], check=True)
print("SUCCESS: stock_video.mp4 ready!")
