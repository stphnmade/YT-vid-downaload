const fs = require("fs");
const path = require("path");
const { app } = require("electron");

function settingsPath() {
  return path.join(app.getPath("userData"), "settings.json");
}

function defaultSettings() {
  return {
    savePath: app.getPath("downloads")
  };
}

function loadSettings() {
  const defaults = defaultSettings();
  try {
    const raw = fs.readFileSync(settingsPath(), "utf8");
    const parsed = JSON.parse(raw);
    return { ...defaults, ...parsed };
  } catch (error) {
    return defaults;
  }
}

function saveSettings(settings) {
  fs.mkdirSync(path.dirname(settingsPath()), { recursive: true });
  fs.writeFileSync(settingsPath(), JSON.stringify(settings, null, 2), "utf8");
}

function setSavePath(savePath) {
  const settings = loadSettings();
  const updated = { ...settings, savePath };
  saveSettings(updated);
  return updated;
}

module.exports = {
  loadSettings,
  setSavePath
};
