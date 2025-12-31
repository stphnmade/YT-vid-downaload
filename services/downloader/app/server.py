import os

from flask import Flask, jsonify, request

from validators import is_valid_youtube_url
from ytdlp_runner import DownloadManager

app = Flask(__name__)
manager = DownloadManager()


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/download")
def start_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    format_name = data.get("format")
    output_dir = data.get("output_dir")

    if not url or not is_valid_youtube_url(url):
        return jsonify({"error": "Enter a valid YouTube URL."}), 400

    if format_name not in ("mp4", "mp3"):
        return jsonify({"error": "Format must be mp4 or mp3."}), 400

    if not output_dir:
        return jsonify({"error": "Save folder is required."}), 400

    os.makedirs(output_dir, exist_ok=True)
    job, error = manager.start_download(url, format_name, output_dir)
    if error:
        return jsonify({"error": error}), 409

    return jsonify({"job": job.to_view().to_dict()})


@app.get("/progress")
def progress():
    job = manager.get_progress()
    if not job:
        return jsonify({"status": "idle"})
    return jsonify(job.to_view().to_dict())


@app.post("/cancel")
def cancel():
    if not manager.cancel_active():
        return jsonify({"error": "No active download to cancel."}), 409
    return jsonify({"status": "cancelling"})


@app.get("/history")
def history():
    return jsonify({"history": [item.to_view().to_dict() for item in manager.get_history()]})


if __name__ == "__main__":
    port = int(os.environ.get("YT_DOWNLOADER_PORT", "4545"))
    host = os.environ.get("YT_DOWNLOADER_HOST", "127.0.0.1")
    app.run(host=host, port=port)
