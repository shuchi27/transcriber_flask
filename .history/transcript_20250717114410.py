import subprocess
import os
import re
import uuid
import sys
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def format_transcript(raw_text):
    lines = raw_text.splitlines()
    cleaned = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Clean up dialogue markers and noise
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


def clean_vtt_to_text(vtt_file):
    text_lines = []
    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '-->' in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
                    continue

                line = re.sub(r'<[^>]+>', '', line)
                line = re.sub(r'\[\s*\]', '', line)
                text_lines.append(line)

        os.remove(vtt_file)
        raw_text = "\n".join(text_lines)
        cleaned_text = format_transcript(raw_text)

        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_dir = os.path.join(desktop_path, "transcript_output")
        os.makedirs(output_dir, exist_ok=True)

        output_file_path = os.path.join(output_dir, "clean_transcript.txt")
        with open(output_file_path, "w", encoding='utf-8') as out:
            out.write(cleaned_text)

        return cleaned_text

    except Exception as e:
        return json.dumps({"error": f"Failed to clean VTT: {e}"})


def download_subtitles(url):
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

def run_whisper_transcription(file_path):
    whisper_model = "base"
    whisper_script = f"""
import whisper
import json

model = whisper.load_model("{whisper_model}")
result = model.transcribe("{file_path}")
print(json.dumps({{"text": result['text']}}))
"""

    temp_script_path = "temp_whisper_script.py"
    with open(temp_script_path, "w") as f:
        f.write(whisper_script)

    try:
        result = subprocess.run(
            ["python3", temp_script_path],
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    finally:
        os.remove(temp_script_path)


def transcribe_with_whisper_audio(video_url, output_path="downloaded_audio.mp3"):
    print("PYTHON OUTPUT: [downloading audio]...")

    try:
        subprocess.run([
            "/Users/home/anaconda3/bin/yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "-o", output_path,
            video_url
        ], check=True)

        return run_whisper_transcription(output_path)

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "URL missing"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    transcript = download_subtitles(url)

    try:
        parsed = json.loads(transcript)
        error_message = parsed.get("error", "")

        if "Subtitles not found." in error_message or "yt-dlp failed" in error_message:
            print("*****************************************************************")
            print("PYTHON OUTPUT: Subtitles not available. Falling back to Whisper (audio only)...")
            whisper_transcript = transcribe_with_whisper_audio(url)
            print(whisper_transcript)
        else:
            print(transcript)
    except json.JSONDecodeError:
        # If it's not a JSON error, assume successful plain transcript
        print(transcript)

