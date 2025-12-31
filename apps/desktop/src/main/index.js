const path = require("path");
const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");

const { loadSettings, setSavePath } = require("./settings");
const { startPythonService } = require("./pythonService");

let mainWindow = null;
let pythonService = null;
let apiBaseUrl = null;

function getBasePath() {
  if (app.isPackaged) {
    return process.resourcesPath;
  }
  return path.resolve(app.getAppPath(), "..", "..");
}

async function apiRequest(endpoint, options = {}) {
  if (!apiBaseUrl) {
    return { ok: false, error: "Downloader service unavailable." };
  }

  const { method = "GET", body } = options;

  try {
    const response = await fetch(`${apiBaseUrl}${endpoint}`, {
      method,
      headers: {
        "Content-Type": "application/json"
      },
      body: body ? JSON.stringify(body) : undefined
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      return {
        ok: false,
        error: data.error || `Request failed (${response.status})`
      };
    }

    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: "Unable to reach downloader service." };
  }
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 980,
    height: 720,
    minWidth: 820,
    minHeight: 640,
    backgroundColor: "#f3f0e8",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(app.getAppPath(), "src", "preload", "index.js")
    }
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    await mainWindow.loadURL(devUrl);
  } else {
    await mainWindow.loadFile(
      path.join(app.getAppPath(), "dist", "renderer", "index.html")
    );
  }
}

app.whenReady().then(async () => {
  const externalApiUrl = process.env.YT_DOWNLOADER_API_URL;
  if (externalApiUrl) {
    apiBaseUrl = externalApiUrl;
  } else {
    try {
      pythonService = await startPythonService({
        basePath: getBasePath()
      });
      apiBaseUrl = pythonService.baseUrl;
    } catch (error) {
      apiBaseUrl = null;
    }
  }

  await createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", () => {
  if (pythonService) {
    pythonService.stop();
  }
});

ipcMain.handle("settings:get", () => {
  return { ok: true, data: loadSettings() };
});

ipcMain.handle("settings:set", (event, savePath) => {
  if (!savePath) {
    return { ok: false, error: "Save path is required." };
  }
  return { ok: true, data: setSavePath(savePath) };
});

ipcMain.handle("settings:select-folder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory", "createDirectory"]
  });

  if (result.canceled || result.filePaths.length === 0) {
    return { ok: true, data: null };
  }

  const selectedPath = result.filePaths[0];
  return { ok: true, data: setSavePath(selectedPath) };
});

ipcMain.handle("download:start", async (event, payload) => {
  return apiRequest("/download", {
    method: "POST",
    body: {
      url: payload.url,
      format: payload.format,
      output_dir: payload.outputDir
    }
  });
});

ipcMain.handle("download:progress", async () => {
  return apiRequest("/progress");
});

ipcMain.handle("download:cancel", async () => {
  return apiRequest("/cancel", { method: "POST" });
});

ipcMain.handle("history:get", async () => {
  return apiRequest("/history");
});

ipcMain.handle("file:open", async (event, filePath) => {
  if (!filePath) {
    return { ok: false, error: "File path is required." };
  }
  await shell.openPath(filePath);
  return { ok: true };
});

ipcMain.handle("folder:open", async (event, filePath) => {
  if (!filePath) {
    return { ok: false, error: "Folder path is required." };
  }
  shell.showItemInFolder(filePath);
  return { ok: true };
});
