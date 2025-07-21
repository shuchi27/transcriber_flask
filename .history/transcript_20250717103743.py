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
    seen = set()

    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '-->' in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
                    continue
                line = re.sub(r'<[^>]+>', '', line)
                if line not in seen:
                    seen.add(line)
                    text_lines.append(line)

        os.remove(vtt_file)

        raw_text = "\n".join(text_lines)
        cleaned_text = format_transcript(raw_text)

        # Save to Desktop
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_dir = os.path.join(desktop_path, "transcript_output")
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, "clean_transcript.txt")
        with open(output_file_path, "w", encoding='utf-8') as out:
            out.write(cleaned_text)

        return cleaned_text

    except Exception as e:
        return json.dumps({"error": f"Failed to clean VTT: {str(e)}"})

def download_subtitles(url):
    uid = str(uuid.uuid4())
    base_path = os.path.join(BASE_DIR, uid)
    vtt_path = f"{base_path}.en.vtt"
    audio_path = f"{base_path}.mp3"
    transcript_txt = f"{base_path}.txt"

    try:
        print("▶️ Trying to download subtitles...")
        subprocess.run(
            [
                "yt-dlp",
                "--write-sub",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "-o", base_path,
                url
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if os.path.exists(vtt_path):
            return clean_vtt_to_text(vtt_path)
        else:
            raise FileNotFoundError("Subtitles not found")

    except Exception as subtitle_error:
        print("⚠️ Subtitles not available. Falling back to audio transcription...")

        try:
            # Download only audio
            subprocess.run(
                [
                    "yt-dlp",
                    "-f", "bestaudio",
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "-o", audio_path,
                    url
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Transcribe with Whisper
            subprocess.run(
                [
                    "whisper", audio_path,
                    "--language", "en",
                    "--model", "base",
                    "--output_format", "txt",
                    "--output_dir", BASE_DIR
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if os.path.exists(transcript_txt):
                with open(transcript_txt, 'r', encoding='utf-8') as f:
                    content = f.read()
                cleaned = format_transcript(content)

                # Save cleaned output to Desktop
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                output_dir = os.path.join(desktop_path, "transcript_output")
                os.makedirs(output_dir, exist_ok=True)
                output_file_path = os.path.join(output_dir, "clean_transcript.txt")
                with open(output_file_path, "w", encoding='utf-8') as out:
                    out.write(cleaned)

                return cleaned
            else:
                return json.dumps({"error": "Whisper transcription file not found."})

        except subprocess.CalledProcessError as whisper_error:
            return json.dumps({"error": f"Audio transcription failed: {whisper_error.stderr.decode('utf-8')}"})
        except Exception as fallback_error:
            return json.dumps({"error": f"Unexpected error during audio fallback: {fallback_error}"})

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "URL missing"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    transcript = download_subtitles(url)
    print(transcript)
