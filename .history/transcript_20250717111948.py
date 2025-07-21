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

                # Remove HTML-like tags like <c>, <00:00:00.000>
                line = re.sub(r'<[^>]+>', '', line)

                # Remove empty or whitespace-only square brackets: [], [   ]
                line = re.sub(r'\[\s*\]', '', line)

                text_lines.append(line)

        os.remove(vtt_file)
        raw_text = "\n".join(text_lines)
        cleaned_text = format_transcript(raw_text)

        # Universal Desktop path (for any user)
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_dir = os.path.join(desktop_path, "transcript_output")
        os.makedirs(output_dir, exist_ok=True)

        output_file_path = os.path.join(output_dir, "clean_transcript.txt")
        with open(output_file_path, "w", encoding='utf-8') as out:
            out.write(cleaned_text)

        return cleaned_text

    except Exception as e:
        return json.dumps({"error": f"Failed to clean VTT: {e}"})

def clean_vtt_to_text_old(vtt_file):
    import re
    import os
    import json

    text_lines = []
    seen = set()

    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip timestamps and metadata
                if not line or '-->' in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
                    continue

                # Remove inline HTML-like tags (e.g., <c>, <00:00:00.000>)
                line = re.sub(r'<[^>]+>', '', line)

                # Normalize whitespace
                line = re.sub(r'\s{2,}', ' ', line).strip()

                # Remove duplicates
                if line and line not in seen:
                    seen.add(line)
                    text_lines.append(line)

        os.remove(vtt_file)

        # Combine into paragraphs and keep speaker labels
        output_lines = []
        current_speaker = None
        buffer = ""

        for line in text_lines:
            # If speaker label like [Mayor Hu]
            if re.match(r'^\[.*\]$', line):
                if buffer:
                    output_lines.append(buffer.strip())
                    buffer = ""
                current_speaker = line.strip("[]")
                continue

            # Add speaker tag to beginning of dialogue
            if current_speaker and not buffer:
                buffer += f"{current_speaker}: "

            buffer += " " + line

        # Add any remaining buffer
        if buffer:
            output_lines.append(buffer.strip())

        cleaned_text = "\n\n".join(output_lines)

        # Save to Desktop
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_dir = os.path.join(desktop_path, "transcript_output")
        os.makedirs(output_dir, exist_ok=True)

        output_file_path = os.path.join(output_dir, "clean_transcript.txt")
        with open(output_file_path, "w", encoding='utf-8') as out:
            out.write(cleaned_text)

        return cleaned_text

    except Exception as e:
        return json.dumps({"error": f"Failed to clean VTT: {e}"})



def clean_vtt_to_text2(vtt_file):
    import re
    import os

    text_lines = []
    seen = set()

    try:
        with open(vtt_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip timestamps and metadata
                if not line or '-->' in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
                    continue

                # Remove tags like <c>, <00:00:00.000>, etc.
                line = re.sub(r'<[^>]+>', '', line)

                # Normalize whitespace
                line = re.sub(r'\s{2,}', ' ', line).strip()

                # Keep unique, non-empty lines
                if line and line not in seen:
                    seen.add(line)
                    text_lines.append(line)

        os.remove(vtt_file)

        # Join lines into coherent paragraphs, preserving speaker labels
        output_lines = []
        buffer = ""
        for line in text_lines:
            if re.match(r"^[A-Za-z\s]+:\s*$", line):  # Speaker label line
                if buffer:
                    output_lines.append(buffer.strip())
                    buffer = ""
                output_lines.append(line)
            else:
                buffer += " " + line
        if buffer:
            output_lines.append(buffer.strip())

        cleaned_text = "\n\n".join(output_lines)

        # Save to Desktop
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
                #"--write-auto-sub",    
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
