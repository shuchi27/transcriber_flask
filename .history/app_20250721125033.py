from flask import Flask, request, Response
import subprocess
import os
import json

app = Flask(__name__)

@app.route("/transcript", methods=["GET"])
def get_transcript():
    url = request.args.get("url")
    if not url:
        return {"error": "Missing URL"}, 400

    try:
        script_path = os.path.join(os.path.dirname(__file__), "transcript.py")

        process = subprocess.Popen(
            ["python3", script_path, url.strip()],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output, _ = process.communicate()
        result = output.decode("utf-8")

        if process.returncode != 0 or '"error"' in result.lower():
            try:
                error_data = json.loads(result)
                error_message = error_data.get("error", "").lower()

                if "yt-dlp failed" in error_message:
                    return {"error": "Invalid URL or video not accessible"}, 400
                elif "subtitles not found" in error_message:
                    return {"error": "No subtitles available for this video"}, 404
                elif "failed to clean vtt" in error_message:
                    return {"error": "Transcript formatting failed"}, 500
                else:
                    return {"error": error_data.get("error", "Unknown error occurred")}, 500

            except json.JSONDecodeError:
                return {"error": "Transcript failed", "details": result}, 500

        # ✅ Success
        return Response(
            result,
            mimetype='text/plain',
            headers={"Content-Disposition": "attachment;filename=transcript.txt"}
        )

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
