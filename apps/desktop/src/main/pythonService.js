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

async function startPythonService({ basePath, port = DEFAULT_PORT }) {
  const scriptPath = path.join(
    basePath,
    "services",
    "downloader",
    "app",
    "server.py"
  );
  const baseUrl = `http://127.0.0.1:${port}`;
  let lastError = null;

  for (const command of pythonCandidates()) {
    const child = spawn(command, [scriptPath], {
      env: {
        ...process.env,
        YT_DOWNLOADER_PORT: String(port),
        PYTHONUNBUFFERED: "1"
      },
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
