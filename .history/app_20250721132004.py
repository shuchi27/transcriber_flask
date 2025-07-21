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
        lines = output.decode("utf-8").splitlines()

        if not lines:
            return {"error": "Transcript failed", "details": "No output received"}, 500

        final_line = lines[-1]  # we assume the last line is your final JSON

        try:
            result_data = json.loads(final_line)
            if "error" in result_data:
                return {"error": result_data.get("error")}, 400
            return Response(
                json.dumps(result_data),
                mimetype='text/plain',
                headers={"Content-Disposition": "attachment;filename=transcript.txt"}
            )
        except json.JSONDecodeError:
            return {"error": "Transcript failed", "details": final_line}, 500
        
        # Success
        return Response(
            result,
            mimetype='text/plain',
            headers={"Content-Disposition": "attachment;filename=transcript.txt"}
        )

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
