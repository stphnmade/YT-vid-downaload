import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dlp.utils import DownloadCancelled


APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import server  # noqa: E402
import ytdlp_runner  # noqa: E402
from validators import is_valid_youtube_url  # noqa: E402


TEST_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


class DownloaderApiTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        server.manager = ytdlp_runner.DownloadManager()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name)

    def tearDown(self):
        server.manager = ytdlp_runner.DownloadManager()
        self.temp_dir.cleanup()

    def test_validators_accept_supported_youtube_urls(self):
        self.assertTrue(is_valid_youtube_url(TEST_URL))
        self.assertTrue(is_valid_youtube_url("https://youtu.be/jNQXAC9IVRw"))
        self.assertTrue(is_valid_youtube_url("https://www.youtube.com/shorts/jNQXAC9IVRw"))
        self.assertFalse(is_valid_youtube_url("https://example.com/watch?v=jNQXAC9IVRw"))
        self.assertFalse(is_valid_youtube_url("not-a-url"))

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_download_validation_errors(self):
        invalid_url = self.client.post(
            "/download",
            json={"url": "https://example.com", "format": "mp4", "output_dir": str(self.output_root)},
        )
        self.assertEqual(invalid_url.status_code, 400)
        self.assertEqual(invalid_url.get_json()["error"], "Enter a valid YouTube URL.")

        invalid_format = self.client.post(
            "/download",
            json={"url": TEST_URL, "format": "wav", "output_dir": str(self.output_root)},
        )
        self.assertEqual(invalid_format.status_code, 400)
        self.assertEqual(invalid_format.get_json()["error"], "Format must be mp4 or mp3.")

        missing_folder = self.client.post("/download", json={"url": TEST_URL, "format": "mp4"})
        self.assertEqual(missing_folder.status_code, 400)
        self.assertEqual(missing_folder.get_json()["error"], "Save folder is required.")

    def test_successful_download_updates_progress_and_history(self):
        output_dir = self.output_root / "success"
        expected_file = output_dir / "fixture.mp4"

        def fake_run(job):
            output_dir.mkdir(parents=True, exist_ok=True)
            expected_file.write_bytes(b"fixture")
            job.status = "downloading"
            job.percent = 42
            job.title = "Fixture Video"
            job.filename = expected_file.name
            job.filepath = str(expected_file)
            time.sleep(0.05)
            job.status = "completed"
            job.percent = 100

        with patch.object(ytdlp_runner, "_run_with_ytdlp", fake_run):
            response = self.client.post(
                "/download",
                json={"url": TEST_URL, "format": "mp4", "output_dir": str(output_dir)},
            )

            self.assertEqual(response.status_code, 200)
            time.sleep(0.15)

        progress = self.client.get("/progress").get_json()
        history = self.client.get("/history").get_json()["history"]

        self.assertEqual(progress["status"], "completed")
        self.assertEqual(progress["filepath"], str(expected_file))
        self.assertTrue(expected_file.exists())
        self.assertEqual(history[0]["status"], "completed")
        self.assertEqual(history[0]["filepath"], str(expected_file))

    def test_rejects_second_download_while_one_is_active(self):
        output_dir = self.output_root / "busy"
        started = threading.Event()
        release = threading.Event()

        def fake_run(job):
            job.status = "downloading"
            job.percent = 5
            started.set()
            release.wait(timeout=2)
            job.status = "completed"
            job.percent = 100

        with patch.object(ytdlp_runner, "_run_with_ytdlp", fake_run):
            first = self.client.post(
                "/download",
                json={"url": TEST_URL, "format": "mp4", "output_dir": str(output_dir)},
            )
            self.assertEqual(first.status_code, 200)
            self.assertTrue(started.wait(timeout=1))

            second = self.client.post(
                "/download",
                json={"url": TEST_URL, "format": "mp3", "output_dir": str(output_dir)},
            )
            self.assertEqual(second.status_code, 409)
            self.assertEqual(second.get_json()["error"], "Another download is already running.")
            release.set()
            time.sleep(0.1)

    def test_cancel_download_marks_history(self):
        output_dir = self.output_root / "cancelled"
        started = threading.Event()

        def fake_run(job):
            job.status = "downloading"
            job.percent = 7
            job.title = "Cancelable"
            job.filename = "cancelable.mp4"
            started.set()
            while not job.cancel_event.is_set():
                time.sleep(0.02)
            raise DownloadCancelled()

        with patch.object(ytdlp_runner, "_run_with_ytdlp", fake_run):
            start_response = self.client.post(
                "/download",
                json={"url": TEST_URL, "format": "mp4", "output_dir": str(output_dir)},
            )
            self.assertEqual(start_response.status_code, 200)
            self.assertTrue(started.wait(timeout=1))

            cancel_response = self.client.post("/cancel")
            self.assertEqual(cancel_response.status_code, 200)
            time.sleep(0.1)

        progress = self.client.get("/progress").get_json()
        history = self.client.get("/history").get_json()["history"]

        self.assertEqual(progress["status"], "cancelled")
        self.assertEqual(progress["error"], "Download cancelled.")
        self.assertEqual(history[0]["status"], "cancelled")
        self.assertEqual(history[0]["error"], "Download cancelled.")

    def test_browser_cookie_copy_error_falls_back_to_plain_download(self):
        job = ytdlp_runner.DownloadJob(TEST_URL, "mp4", str(self.output_root))
        calls = []
        fallback_path = self.output_root / "fallback.mp4"
        original_exists = ytdlp_runner.os.path.exists

        class FakeYoutubeDL:
            def __init__(self, opts):
                self.opts = opts
                calls.append(opts.copy())

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, url, download=True):
                if self.opts.get("cookiesfrombrowser"):
                    raise Exception("ERROR: Could not copy Chrome cookie database.")
                return {"title": "Fallback Works"}

            def prepare_filename(self, info):
                return str(fallback_path)

        with (
            patch.object(ytdlp_runner, "YoutubeDL", FakeYoutubeDL),
            patch.object(ytdlp_runner, "_load_cookie_settings_from_config", return_value=(None, "chrome")),
            patch.dict(ytdlp_runner.os.environ, {}, clear=True),
            patch.object(
                ytdlp_runner.os.path,
                "exists",
                side_effect=lambda value: False
                if str(value).endswith(("cookies.txt", "cookies"))
                else original_exists(value),
            ),
        ):
            ytdlp_runner._run_with_ytdlp(job)

        self.assertEqual(job.status, "completed")
        self.assertEqual(job.filename, "fallback.mp4")
        self.assertEqual(len(calls), 2)
        self.assertIn("cookiesfrombrowser", calls[0])
        self.assertNotIn("cookiesfrombrowser", calls[1])

    def test_auto_browser_cookie_detection_is_disabled_by_default(self):
        job = ytdlp_runner.DownloadJob(TEST_URL, "mp4", str(self.output_root))
        seen_opts = []
        plain_path = self.output_root / "plain.mp4"

        class FakeYoutubeDL:
            def __init__(self, opts):
                self.opts = opts
                seen_opts.append(opts.copy())

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def extract_info(self, url, download=True):
                return {"title": "No Auto Cookies"}

            def prepare_filename(self, info):
                return str(plain_path)

        with (
            patch.object(ytdlp_runner, "YoutubeDL", FakeYoutubeDL),
            patch.object(ytdlp_runner, "_load_cookie_settings_from_config", return_value=(None, None)),
            patch.object(ytdlp_runner, "_detect_cookies_browser", return_value="chrome"),
            patch.dict(ytdlp_runner.os.environ, {}, clear=True),
        ):
            ytdlp_runner._run_with_ytdlp(job)

        self.assertEqual(job.status, "completed")
        self.assertEqual(len(seen_opts), 1)
        self.assertNotIn("cookiesfrombrowser", seen_opts[0])


if __name__ == "__main__":
    unittest.main()
