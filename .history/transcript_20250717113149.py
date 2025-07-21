import subprocess
import os
import re
import uuid
import sys
import json
from urllib.parse import urlparse

# Only import if YouTube
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def format_transcript(raw_text):
    lines = raw_text.splitlines()
    cleaned = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        line = re.sub(r'^>>\s*', '', line)
        line = re.sub(r'\s*>>\s*', ' ', line)
        line = re.sub(r':\s*\.', ':', line)
        line = re.sub(r'\.\.+', '.', line)
        line = re.sub(r'\s{2,}', ' ', line)
        line = re.sub(r'\s*:\s*$', '', line)
        line = re.sub(r'\s*–\s*', '-', line)
        line = re.sub(r'\s+', ' ', line)

        if line:
            line = line[0].upper() + line[1:] if not line.isupper() else line
            cleaned.append(line)

    return "\n\n".join(cleaned)

def save_to_desktop(text):
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    output_dir = os.path.join(desktop_path, "transcript_output")
    os.makedirs(output_dir, exist_ok=True)
    output_file_path = os.path.join(output_dir, "clean_transcript.txt")
    with open(output_file_path, "w", encoding="utf-8") as out:
        out.write(text)

def clean_vtt_to_text(vtt_file):
    text_lines = []
    seen = set()

    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '-->' in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
                    continue

                line = re.sub(r'<[^>]+>', '', line)  # remove <c> tags
                line = re.sub(r'\[\s*\]', '', line)  # remove empty [ ]
                if line and line not in seen:
                    seen.add(line)
                    text_lines.append(line)

        os.remove(vtt_file)
        raw_text = "\n".join(text_lines)
        cleaned_text = format_transcript(raw_text)
        save_to_desktop(cleaned_text)
        return cleaned_text

    except Exception as e:
        return json.dumps({"error": f"Failed to clean VTT: {e}"})


def download_youtube_transcript(url):
    try:
        video_id = extract_youtube_id(url)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        raw_lines = [entry['text'] for entry in transcript if entry['text'].strip()]
        raw_text = "\n".join(raw_lines)
        cleaned_text = format_transcript(raw_text)
        save_to_desktop(cleaned_text)
        return cleaned_text
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch YouTube transcript: {e}"})


def extract_youtube_id(url):
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        query = parsed_url.query
        return dict(qc.split("=") for qc in query.split("&")).get("v")
    elif 'youtu.be' in parsed_url.netloc:
        return parsed_url.path.strip("/")
    return None


def download_subtitles(url):
    if "youtube.com" in url or "youtu.be" in url:
        return download_youtube_transcript(url)

    uid = str(uuid.uuid4())
    vtt_filename = f"{uid}.en.vtt"
    output_path = os.path.join(BASE_DIR, vtt_filename)

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--write-sub",
                "--sub-lang", "en",
                "--skip-download",
                "-o", os.path.join(BASE_DIR, uid),
                url
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if os.path.exists(output_path):
            return clean_vtt_to_text(output_path)
        else:
            return json.dumps({"error": "Subtitles not found."})

    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"yt-dlp failed: {e.stderr.decode('utf-8')}"})


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "URL missing"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    transcript = download_subtitles(url)
    print(transcript)
