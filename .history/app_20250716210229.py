from flask import Flask, request, Response
import subprocess
import os

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

        if process.returncode != 0 or "\"error\"" in result:
            return {"error": "Transcript failed", "details": result}, 500

        return Response(
            result,
            mimetype='text/plain',
            headers={"Content-Disposition": "attachment;filename=transcript.txt"}
        )

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
