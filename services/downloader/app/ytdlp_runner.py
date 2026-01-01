import glob
import os
import threading
import time
import uuid
from collections import deque

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

from models import DownloadJobView


class DownloadJob:
    def __init__(self, url: str, format_name: str, output_dir: str) -> None:
        self.id = str(uuid.uuid4())
        self.url = url
        self.format = format_name
        self.output_dir = output_dir
        self.status = "queued"
        self.percent = 0
        self.title = None
        self.filename = None
        self.filepath = None
        self.error = None
        self.created_at = time.time()
        self.cancel_event = threading.Event()

    def to_view(self) -> DownloadJobView:
        return DownloadJobView(
            id=self.id,
            url=self.url,
            format=self.format,
            status=self.status,
            percent=int(self.percent),
            title=self.title,
            filename=self.filename,
            filepath=self.filepath,
            error=self.error,
        )


def _any_path_exists(paths) -> bool:
    return any(path and os.path.exists(path) for path in paths)


def _firefox_cookie_exists(profile_root: str) -> bool:
    if not profile_root:
        return False
    pattern = os.path.join(profile_root, "Profiles", "*", "cookies.sqlite")
    return bool(glob.glob(pattern))


def _detect_cookies_browser() -> str | None:
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        roaming = os.environ.get("APPDATA", "")
        if _any_path_exists(
            [
                os.path.join(local, "Google", "Chrome", "User Data", "Default", "Network", "Cookies"),
                os.path.join(local, "Google", "Chrome", "User Data", "Default", "Cookies"),
            ]
        ):
            return "chrome"
        if _any_path_exists(
            [
                os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Network", "Cookies"),
                os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Cookies"),
            ]
        ):
            return "edge"
        if _firefox_cookie_exists(os.path.join(roaming, "Mozilla", "Firefox")):
            return "firefox"
        return None

    home = os.path.expanduser("~")
    if os.path.exists(os.path.join(home, "Library", "Application Support")):
        if _any_path_exists(
            [
                os.path.join(
                    home,
                    "Library",
                    "Application Support",
                    "Google",
                    "Chrome",
                    "Default",
                    "Network",
                    "Cookies",
                ),
                os.path.join(
                    home,
                    "Library",
                    "Application Support",
                    "Google",
                    "Chrome",
                    "Default",
                    "Cookies",
                ),
            ]
        ):
            return "chrome"
        if _any_path_exists(
            [
                os.path.join(
                    home,
                    "Library",
                    "Application Support",
                    "Microsoft Edge",
                    "Default",
                    "Network",
                    "Cookies",
                ),
                os.path.join(
                    home,
                    "Library",
                    "Application Support",
                    "Microsoft Edge",
                    "Default",
                    "Cookies",
                ),
            ]
        ):
            return "edge"
        if _firefox_cookie_exists(os.path.join(home, "Library", "Application Support", "Firefox")):
            return "firefox"
        return None

    if _any_path_exists(
        [
            os.path.join(home, ".config", "google-chrome", "Default", "Network", "Cookies"),
            os.path.join(home, ".config", "google-chrome", "Default", "Cookies"),
        ]
    ):
        return "chrome"
    if _any_path_exists(
        [
            os.path.join(home, ".config", "chromium", "Default", "Network", "Cookies"),
            os.path.join(home, ".config", "chromium", "Default", "Cookies"),
        ]
    ):
        return "chromium"
    if _firefox_cookie_exists(os.path.join(home, ".mozilla", "firefox")):
        return "firefox"
    return None


def _extract_config_value(line: str) -> str | None:
    if "=" in line:
        _, value = line.split("=", 1)
    else:
        parts = line.split(None, 1)
        if len(parts) < 2:
            return None
        value = parts[1]
    value = value.strip().strip('"').strip("'")
    return value or None


def _load_cookie_settings_from_config() -> tuple[str | None, str | None]:
    config_path = os.environ.get("YT_DLP_CONFIG")
    if not config_path:
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "yt-dlp.conf"))
    if not config_path or not os.path.exists(config_path):
        return None, None

    cookiefile = None
    cookiesfrombrowser = None
    with open(config_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("--cookies-from-browser"):
                value = _extract_config_value(line)
                if value:
                    cookiesfrombrowser = value
                continue
            if line.startswith("--cookies"):
                value = _extract_config_value(line)
                if value:
                    if not os.path.isabs(value):
                        value = os.path.abspath(os.path.join(os.path.dirname(config_path), value))
                    cookiefile = value

    return cookiefile, cookiesfrombrowser


def _run_with_ytdlp(job: DownloadJob) -> None:
    def progress_hook(data: dict) -> None:
        if job.cancel_event.is_set():
            raise DownloadCancelled()

        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = int(downloaded * 100 / total) if total else 0
            job.status = "downloading"
            job.percent = percent
            filename = data.get("filename")
            if filename:
                job.filepath = filename
                job.filename = os.path.basename(filename)
        elif status == "finished":
            job.status = "processing"
            job.percent = 100

    ydl_opts = {
        "outtmpl": os.path.join(job.output_dir, "%(title).200B.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
    }

    config_cookie_file, config_cookies_from_browser = _load_cookie_settings_from_config()
    env_cookie_file = os.environ.get("YT_DLP_COOKIES")
    cookie_file = env_cookie_file or config_cookie_file
    cookies_from_browser = os.environ.get("YT_DLP_COOKIES_BROWSER") or config_cookies_from_browser
    if cookie_file and not os.path.exists(cookie_file):
        if env_cookie_file:
            raise FileNotFoundError(f"YT_DLP_COOKIES not found at: {cookie_file}")
        cookie_file = None
    if not cookie_file:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        for name in ("cookies.txt", "cookies"):
            candidate = os.path.join(repo_root, name)
            if os.path.exists(candidate):
                cookie_file = candidate
                break
    if cookie_file:
        ydl_opts["cookiefile"] = cookie_file
    elif cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
    else:
        detected_browser = _detect_cookies_browser()
        if detected_browser:
            ydl_opts["cookiesfrombrowser"] = (detected_browser,)

    if job.format == "mp3":
        ydl_opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "0",
                    }
                ],
            }
        )
    else:
        ydl_opts.update(
            {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "merge_output_format": "mp4",
            }
        )

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(job.url, download=True)
        job.title = info.get("title")
        filepath = ydl.prepare_filename(info)
        if job.format == "mp3":
            filepath = f"{os.path.splitext(filepath)[0]}.mp3"
        job.filepath = filepath
        job.filename = os.path.basename(filepath)

    job.status = "completed"
    job.percent = 100


class DownloadManager:
    def __init__(self, history_size: int = 20) -> None:
        self.active = None
        self.history = deque(maxlen=history_size)
        self.lock = threading.Lock()

    def start_download(self, url: str, format_name: str, output_dir: str):
        with self.lock:
            if self.active and self.active.status in ("downloading", "processing"):
                return None, "Another download is already running."

            job = DownloadJob(url, format_name, output_dir)
            self.active = job

        thread = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        thread.start()
        return job, None

    def _run_job(self, job: DownloadJob) -> None:
        try:
            _run_with_ytdlp(job)
        except DownloadCancelled:
            job.status = "cancelled"
            job.error = "Download cancelled."
        except Exception as exc:
            job.status = "error"
            job.error = str(exc)
        finally:
            with self.lock:
                self.history.appendleft(job)

    def cancel_active(self) -> bool:
        with self.lock:
            if not self.active or self.active.status not in ("downloading", "processing"):
                return False
            self.active.cancel_event.set()
            return True

    def get_progress(self):
        with self.lock:
            return self.active

    def get_history(self):
        with self.lock:
            return list(self.history)
