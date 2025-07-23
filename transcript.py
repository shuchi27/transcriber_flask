import requests
import subprocess
import os
import re
import uuid
import sys
import json
import logging
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#changes reflecteddddddddddd************************************
# Set up logging to file
log_file_path = os.path.join(BASE_DIR, "transcript_debug.log")
logging.basicConfig(
    filename=log_file_path,
    filemode='a',  # Append mode
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def get_transcript_youtube_api(url):
    try:
        # Extract video ID from YouTube URL
        logging.info("Using youtube_transcript_api fallback...")  
        query = urlparse(url)
        if query.hostname in ['www.youtube.com', 'youtube.com']:
            video_id = parse_qs(query.query).get("v", [None])[0]
        elif query.hostname in ['youtu.be']:
            video_id = query.path[1:]
        else:
            return None

        if not video_id:
            return None

        # Fetch transcript using API
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        full_text = "\n".join([entry["text"] for entry in transcript])
        return full_text

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        print(f"[youtube_transcript_api] Transcript not found or disabled: {e}")
        return None
    except Exception as e:
        print(f"[youtube_transcript_api] Failed: {e}")
        return None

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
    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '-->' in line:
                    continue

                line = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', line)
                line = re.sub(r'</?[a-zA-Z0-9]>', '', line)
                line = re.sub(r'\[\s*&nbsp;.*?&nbsp;\s*\]', '', line, flags=re.IGNORECASE)
                if re.match(r'^\[\s*\]$', line):
                    continue

                text_lines.append(line)

        os.remove(vtt_file)
        raw_text = "\n".join(text_lines)
        cleaned_text = format_transcript(raw_text)

        output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "transcript_output")
        os.makedirs(output_dir, exist_ok=True)

        output_file_path = os.path.join(output_dir, "clean_transcript.txt")
        with open(output_file_path, "w", encoding='utf-8') as out:
            out.write(cleaned_text)

        return cleaned_text

    except Exception as e:
        return json.dumps({"error": f"Failed to clean VTT: {e}"})

def run_whisper_transcription(file_path):
    whisper_model = "base"
    whisper_script = f"""
import whisper, json
model = whisper.load_model("{whisper_model}")
result = model.transcribe("{file_path}")
print(json.dumps({{"text": result['text']}}))
"""
    temp_script_path = "temp_whisper_script.py"
    with open(temp_script_path, "w") as f:
        f.write(whisper_script)

    try:
        result = subprocess.run(["python3", temp_script_path], check=True, capture_output=True, text=True)
        return result.stdout
    finally:
        os.remove(temp_script_path)

def transcribe_with_whisper_audio(video_url):
    #print("PYTHON OUTPUT: [downloading audio]...")
    uid = str(uuid.uuid4())
    output_path = f"transcribed_audio_{uid}.mp3"

    try:
        subprocess.run([
            "yt-dlp",
            "--cookies", "youtube.com_cookies.txt",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "--no-playlist",
            "-o", output_path,
            video_url
        ], check=True)
        return run_whisper_transcription(output_path)

    except subprocess.CalledProcessError:
        return json.dumps({"error": "yt-dlp audio extraction failed and no fallback media extractor is defined."})

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

def download_subtitles(url):
    if url.endswith(".vtt"):
        return download_vtt_and_process(url)

    uid = str(uuid.uuid4())
    vtt_filename = f"{uid}.en.vtt"
    output_path = os.path.join(BASE_DIR, vtt_filename)

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--write-sub",
                "--write-auto-sub",
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
            logging.warning(f"yt-dlp ran, but .vtt file not found at: {output_path}")
            return json.dumps({"error": "Subtitles not found."})

    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"yt-dlp failed: {e.stderr.decode('utf-8')}"})

def download_vtt_and_process(vtt_url):
    try:
        logging.info(f"Downloading direct VTT file: {vtt_url}")
        vtt_response = requests.get(vtt_url, timeout=10)
        if vtt_response.status_code != 200:
            return json.dumps({"error": f"Failed to download VTT (HTTP {vtt_response.status_code})"})

        temp_vtt_path = os.path.join(BASE_DIR, f"{str(uuid.uuid4())}.vtt")
        with open(temp_vtt_path, "wb") as f:
            f.write(vtt_response.content)

        return clean_vtt_to_text(temp_vtt_path)

    except Exception as e:
        return json.dumps({"error": f"Exception while downloading VTT: {e}"})

def extract_vtt_from_html_page(url):
    try:
        logging.info(f"Scanning HTML source for VTT: {url}")
        response = requests.get(url, timeout=10)
        vtt_matches = re.findall(r'https?://[^\s\'"]+\.vtt', response.text)
        if vtt_matches:
            full_vtt_url = vtt_matches[0]
            logging.info(f"Found VTT in HTML: {full_vtt_url}")

            head_resp = requests.head(full_vtt_url, timeout=5)
            if head_resp.status_code == 200:
                return full_vtt_url
            else:
                logging.warning(f"VTT exists but not downloadable (HTTP {head_resp.status_code})")
    except Exception as e:
        logging.error(f"HTML scan failed: {e}")
    return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "URL missing"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    logging.info(f"Starting transcript extraction for: {url}")

    # Step 1: Try subtitles using yt-dlp
    transcript = download_subtitles(url)

    try:
        parsed = json.loads(transcript)
        if "error" in parsed:
            logging.warning("Subtitles not found. Trying HTML page scan for .vtt...")
            vtt_url = extract_vtt_from_html_page(url)

            if vtt_url:
                logging.info(f"Retrying with direct VTT URL: {vtt_url}")
                transcript = download_vtt_and_process(vtt_url)
                parsed = json.loads(transcript)

        # Step 1.5: Try youtube_transcript_api as an additional fallback
        if "error" in parsed:
            logging.warning("Trying youtube_transcript_api fallback...")
            yt_api_result = get_transcript_youtube_api(url)
            
            if yt_api_result:
                transcript = json.dumps({"text": yt_api_result})
                print(transcript)
                sys.exit(0)

        # Step 2: Fallback to Whisper if still failed
        if "error" in parsed:
            logging.warning("Falling back to Whisper (audio transcription)...")
            transcript = transcribe_with_whisper_audio(url)

        print(transcript)

    except json.JSONDecodeError:
        logging.error("Transcript output was not JSON — printing raw result.")
        print(transcript)

