const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const DEFAULT_PORT = 4545;
const START_TIMEOUT_MS = 8000;
const HEALTH_ENDPOINT = "/health";

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForHealthy(baseUrl, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(`${baseUrl}${HEALTH_ENDPOINT}`);
      if (response.ok) {
        return true;
      }
    } catch (error) {
      // Keep polling until timeout.
    }
    await delay(300);
  }
  return false;
}

function pythonCandidates() {
  if (process.platform === "win32") {
    return ["python"];
  }
  return ["python3", "python"];
}

function ffmpegBinaryNames() {
  if (process.platform === "win32") {
    return ["ffmpeg.exe", "ffprobe.exe"];
  }
  return ["ffmpeg", "ffprobe"];
}

function ffmpegTargetKeys() {
  if (process.platform === "darwin") {
    return [`darwin-${process.arch}`, "darwin-universal", "darwin"];
  }
  if (process.platform === "win32") {
    return [`win32-${process.arch}`, "win32"];
  }
  return [];
}

function containsFfmpegBundle(dirPath) {
  return ffmpegBinaryNames().every((name) => fs.existsSync(path.join(dirPath, name)));
}

function getBundledFfmpegLocation(basePath) {
  const searchRoots = [
    path.join(basePath, "ffmpeg"),
    path.join(basePath, "apps", "desktop", "resources", "ffmpeg")
  ];

  for (const root of searchRoots) {
    for (const key of ffmpegTargetKeys()) {
      const candidate = path.join(root, key);
      if (containsFfmpegBundle(candidate)) {
        return candidate;
      }
    }
  }

  return null;
}

async function startPythonService({ basePath, port = DEFAULT_PORT }) {
  const scriptPath = path.join(
    basePath,
    "services",
    "downloader",
    "app",
    "server.py"
  );
  const baseUrl = `http://127.0.0.1:${port}`;
  const bundledFfmpegLocation =
    process.env.YT_DLP_FFMPEG_LOCATION || getBundledFfmpegLocation(basePath);
  let lastError = null;

  for (const command of pythonCandidates()) {
    const childEnv = {
      ...process.env,
      YT_DOWNLOADER_PORT: String(port),
      PYTHONUNBUFFERED: "1"
    };
    if (bundledFfmpegLocation) {
      childEnv.YT_DLP_FFMPEG_LOCATION = bundledFfmpegLocation;
    }

    const child = spawn(command, [scriptPath], {
      env: childEnv,
      stdio: ["ignore", "pipe", "pipe"]
    });

    child.on("error", (error) => {
      lastError = error;
    });

    const ready = await waitForHealthy(baseUrl, START_TIMEOUT_MS);
    if (ready) {
      return {
        child,
        baseUrl,
        stop: () => child.kill()
      };
    }

    child.kill();
  }

  if (lastError) {
    throw lastError;
  }

  throw new Error("Unable to start downloader service.");
}

module.exports = {
  startPythonService
};
