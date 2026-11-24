import os
import json
from pathlib import Path
from google import genai
from google.genai import types

topic = os.environ.get("TOPIC", "").strip()
if not topic:
    print("No topic provided, keeping existing story.json")
    raise SystemExit(0)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

prompt = f"""You are a YouTube Shorts Automation AI.
Create a 6-scene vertical (9:16) animated stick-figure video for the topic: "{topic}"

Return ONLY valid JSON with this exact schema:
{{
  "width": 720,
  "height": 1280,
  "voice": "en-US-AndrewNeural",
  "scenes": [
    {{
      "narration": "Short punchy US English sentence under 160 characters.",
      "html": "<!DOCTYPE html><html>...</html>"
    }}
  ]
}}

Rules for each scene's "html":
1. Self-contained HTML/SVG with <svg id="s" width="720" height="1280" viewBox="0 0 360 640"></svg>.
2. Must define window.renderAt = (t, d) => {{ ... }} and call renderAt(0, 4) at the end.
3. Animate a 2D stick-figure / cartoon character (breathing, blinking, moving arms/props) using Math.sin(t * ...) and show bold white centered captions at the bottom (y=530) matching the narration.
4. Keep each scene's HTML compact on a single string without broken quotes."""

resp = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=prompt,
    config=types.GenerateContentConfig(response_mime_type="application/json"),
)

data = json.loads(resp.text)
Path("story.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Generated {len(data['scenes'])} scenes for topic: {topic}")

