import argparse
import json
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "services" / "downloader" / "app"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import server  # noqa: E402
import ytdlp_runner  # noqa: E402


DEFAULT_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a repeatable backend smoke test for MP4 and MP3 downloads."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="YouTube URL to test.")
    parser.add_argument(
        "--format",
        dest="formats",
        action="append",
        choices=("mp4", "mp3"),
        help="Format to test. Repeat to test both. Defaults to mp4 and mp3.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=240,
        help="Seconds to wait per download before failing.",
    )
    parser.add_argument(
        "--output-root",
        default=str(REPO_ROOT / "tmp" / "smoke-downloads"),
        help="Directory where smoke-test outputs will be written.",
    )
    parser.add_argument(
        "--ffmpeg-location",
        help="Directory or binary path to use for FFmpeg during MP3 smoke tests.",
    )
    parser.add_argument(
        "--cookies",
        help="Optional cookie file path to pass through as YT_DLP_COOKIES.",
    )
    parser.add_argument(
        "--cookies-browser",
        choices=("chrome", "edge", "firefox", "chromium"),
        help="Optional browser name to pass through as YT_DLP_COOKIES_BROWSER.",
    )
    return parser.parse_args()


def configure_environment(args):
    if args.ffmpeg_location:
        os.environ["YT_DLP_FFMPEG_LOCATION"] = args.ffmpeg_location
    if args.cookies:
        os.environ["YT_DLP_COOKIES"] = args.cookies
    if args.cookies_browser:
        os.environ["YT_DLP_COOKIES_BROWSER"] = args.cookies_browser


def poll_until_terminal(client, timeout_seconds):
    deadline = time.time() + timeout_seconds
    samples = []

    while time.time() < deadline:
        response = client.get("/progress")
        payload = response.get_json()
        samples.append(payload)
        if payload.get("status") in {"completed", "error", "cancelled"}:
            return payload, samples
        time.sleep(1)

    return None, samples


def run_download(client, url, format_name, output_dir, timeout_seconds):
    server.manager = ytdlp_runner.DownloadManager()
    output_dir.mkdir(parents=True, exist_ok=True)

    response = client.post(
        "/download",
        json={
            "url": url,
            "format": format_name,
            "output_dir": str(output_dir),
        },
    )

    terminal, samples = (None, [])
    if response.status_code == 200:
        terminal, samples = poll_until_terminal(client, timeout_seconds)
        time.sleep(0.5)

    history = client.get("/history").get_json().get("history", [])
    filepath = terminal.get("filepath") if terminal else None
    file_path_obj = Path(filepath) if filepath else None
    return {
        "format": format_name,
        "start_status": response.status_code,
        "start_body": response.get_json(),
        "terminal": terminal,
        "history_head": history[0] if history else None,
        "file_exists": bool(file_path_obj and file_path_obj.exists()),
        "file_size": file_path_obj.stat().st_size if file_path_obj and file_path_obj.exists() else None,
        "output_dir": str(output_dir),
        "progress_samples": samples[-8:],
    }


def main():
    args = parse_args()
    configure_environment(args)

    formats = args.formats or ["mp4", "mp3"]
    run_root = Path(args.output_root) / time.strftime("%Y%m%d-%H%M%S")
    client = server.app.test_client()

    results = [
        run_download(client, args.url, format_name, run_root / format_name, args.timeout)
        for format_name in formats
    ]

    summary = {
        "url": args.url,
        "formats": formats,
        "ffmpeg_location": os.environ.get("YT_DLP_FFMPEG_LOCATION"),
        "output_root": str(run_root),
        "passed": all(
            item["start_status"] == 200
            and item["terminal"] is not None
            and item["terminal"].get("status") == "completed"
            and item["file_exists"]
            for item in results
        ),
        "results": results,
    }

    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
