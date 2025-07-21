import subprocess
import os
import re
import uuid
import sys
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def format_transcript_with_labels(text_lines):
    output_lines = []
    buffer = ""
    current_speaker = None

    for line in text_lines:
        if re.match(r"^[A-Z][A-Za-z ]{1,40}:", line):
            if buffer:
                output_lines.append(buffer.strip())
                buffer = ""
            current_speaker = line.split(":")[0].strip()
            buffer = f"{current_speaker}: {line.split(':', 1)[1].strip()}"
        else:
            buffer += f" {line.strip()}"

    if buffer:
        output_lines.append(buffer.strip())

    return "\n\n".join(output_lines)

def clean_vtt_to_text(vtt_file):
    text_lines = []
    seen = set()
    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '-->' in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
                    continue
                line = re.sub(r'<[^>]+>', '', line)
                line = re.sub(r'\s{2,}', ' ', line).strip()
                if line and line not in seen:
                    seen.add(line)
                    text_lines.append(line)

        os.remove(vtt_file)
        cleaned_text = format_transcript_with_labels(text_lines)

        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_dir = os.path.join(desktop_path, "transcript_output")
        os.makedirs(output_dir, exist_ok=True)

        output_file_path = os.path.join(output_dir, "clean_transcript.txt")
        with open(output_file_path, "w", encoding='utf-8') as out:
            out.write(cleaned_text)

        return cleaned_text

    except Exception as e:
        return json.dumps({"error": f"Failed to clean VTT: {e}"})

def fallback_to_whisper(url, audio_path):
    try:
        subprocess.run([
            "yt-dlp", "-x", "--audio-format", "mp3", "-o", audio_path, url
        ], check=True)

        subprocess.run([
            "whisper", f"{audio_path}.mp3", "--language", "en", "--output_format", "txt"
        ], check=True)

        transcript_path = f"{audio_path}.txt"
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r', encoding='utf-8') as f:
                return f.read()

        return json.dumps({"error": "Whisper transcription not found."})

    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"Whisper fallback failed: {e.stderr if e.stderr else e}"})

def download_subtitles(url):
    uid = str(uuid.uuid4())
    vtt_filename = f"{uid}.en.vtt"
    output_path = os.path.join(BASE_DIR, vtt_filename)

    try:
        subprocess.run([
            "yt-dlp", "--write-sub", "--write-auto-sub", "--sub-lang", "en",
            "--skip-download", "-o", os.path.join(BASE_DIR, uid), url
        ], check=True)

        if os.path.exists(output_path):
            return clean_vtt_to_text(output_path)
        else:
            # fallback to whisper if subtitles not found
            audio_path = os.path.join(BASE_DIR, uid)
            return fallback_to_whisper(url, audio_path)

    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"yt-dlp failed: {e.stderr.decode('utf-8') if e.stderr else str(e)}"})

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "URL missing"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    transcript = download_subtitles(url)
    print(transcript)
