import json
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

WORK = Path("build_tmp")
AUD_DIR = WORK / "audio"
FRM_DIR = WORK / "frames"
CLIP_DIR = WORK / "clips"
for d in (AUD_DIR, FRM_DIR, CLIP_DIR):
    d.mkdir(parents=True, exist_ok=True)

story = json.loads(Path("story.json").read_text(encoding="utf-8"))
W, H = story.get("width", 720), story.get("height", 1280)
FPS = 24
VOICE = story.get("voice", "en-US-AndrewNeural")

def get_dur(mp3_path: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)],
        capture_output=True, text=True, check=True
    )
    return float(res.stdout.strip())

clip_paths = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": W, "height": H})

    for idx, sc in enumerate(story["scenes"], start=1):
        mp3_path = AUD_DIR / f"scene_{idx:02d}.mp3"
        subprocess.run([
            "edge-tts", "--voice", VOICE,
            "--text", sc["narration"], "--write-media", str(mp3_path)
        ], check=True)
        dur = get_dur(mp3_path) + 0.25
        total_frames = int(dur * FPS)

        html_file = WORK / f"scene_{idx:02d}.html"
        html_file.write_text(sc["html"], encoding="utf-8")
        page.goto(html_file.resolve().as_uri())

        sc_frames = FRM_DIR / f"s_{idx:02d}"
        sc_frames.mkdir(parents=True, exist_ok=True)
        for f in range(total_frames):
            t_sec = f / FPS
            page.evaluate(f"if (window.renderAt) window.renderAt({t_sec:.4f}, {dur:.4f});")
            page.screenshot(path=str(sc_frames / f"f_{f:04d}.png"))

        clip_mp4 = CLIP_DIR / f"clip_{idx:02d}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(sc_frames / "f_%04d.png"), "-i", str(mp3_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", str(clip_mp4)
        ], check=True)
        clip_paths.append(clip_mp4)
        print(f"Rendered Scene {idx}/{len(story['scenes'])} ({dur:.2f}s)")

    browser.close()

concat_txt = WORK / "concat.txt"
concat_txt.write_text("\n".join([f"file '{c.resolve()}'" for c in clip_paths]), encoding="utf-8")

subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
    "-c", "copy", "-movflags", "+faststart", "final_video.mp4"
], check=True)
print("SUCCESS: final_video.mp4 ready!")

