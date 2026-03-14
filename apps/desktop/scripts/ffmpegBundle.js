const fs = require("fs");
const path = require("path");
const { Arch } = require("builder-util");

const APP_DIR = path.resolve(__dirname, "..");
const STAGING_ROOT = path.join(APP_DIR, "resources", "ffmpeg");

const TARGETS = {
  "win32-x64": {
    envVar: "YT_DLP_FFMPEG_WIN_X64_SOURCE",
    binaries: ["ffmpeg.exe", "ffprobe.exe"]
  },
  "win32-arm64": {
    envVar: "YT_DLP_FFMPEG_WIN_ARM64_SOURCE",
    binaries: ["ffmpeg.exe", "ffprobe.exe"]
  },
  "darwin-x64": {
    envVar: "YT_DLP_FFMPEG_MAC_X64_SOURCE",
    binaries: ["ffmpeg", "ffprobe"]
  },
  "darwin-arm64": {
    envVar: "YT_DLP_FFMPEG_MAC_ARM64_SOURCE",
    binaries: ["ffmpeg", "ffprobe"]
  },
  "darwin-universal": {
    envVar: "YT_DLP_FFMPEG_MAC_UNIVERSAL_SOURCE",
    binaries: ["ffmpeg", "ffprobe"]
  }
};

function ensureDirectory(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function targetDir(targetKey) {
  return path.join(STAGING_ROOT, targetKey);
}

function missingBinaries(targetKey) {
  const target = TARGETS[targetKey];
  if (!target) {
    throw new Error(`Unsupported FFmpeg bundle target: ${targetKey}`);
  }

  const dir = targetDir(targetKey);
  return target.binaries.filter((name) => !fs.existsSync(path.join(dir, name)));
}

function clearManagedFiles(targetKey) {
  const dir = targetDir(targetKey);
  if (!fs.existsSync(dir)) {
    return;
  }

  for (const entry of fs.readdirSync(dir)) {
    if (entry === ".gitkeep") {
      continue;
    }
    fs.rmSync(path.join(dir, entry), { recursive: true, force: true });
  }
}

function copyBundle(sourceDir, targetKey) {
  const target = TARGETS[targetKey];
  const resolvedSource = path.resolve(sourceDir);

  if (!fs.existsSync(resolvedSource)) {
    throw new Error(`FFmpeg source directory does not exist: ${resolvedSource}`);
  }

  ensureDirectory(targetDir(targetKey));
  clearManagedFiles(targetKey);

  for (const entry of fs.readdirSync(resolvedSource)) {
    fs.cpSync(path.join(resolvedSource, entry), path.join(targetDir(targetKey), entry), {
      recursive: true
    });
  }

  for (const binary of target.binaries) {
    const sourceFile = path.join(resolvedSource, binary);
    if (!fs.existsSync(sourceFile)) {
      throw new Error(
        `Missing ${binary} in ${resolvedSource}. Expected binaries: ${target.binaries.join(", ")}`
      );
    }
  }
}

function sourceDirFor(targetKey) {
  const target = TARGETS[targetKey];
  return process.env[target.envVar] || process.env.YT_DLP_FFMPEG_SOURCE || null;
}

function stageBundle(targetKey, options = {}) {
  const { required = false } = options;
  const sourceDir = sourceDirFor(targetKey);

  if (sourceDir) {
    copyBundle(sourceDir, targetKey);
  }

  const missing = missingBinaries(targetKey);
  if (missing.length > 0) {
    if (!required) {
      return {
        ok: false,
        targetKey,
        targetDir: targetDir(targetKey),
        missing
      };
    }

    const envVar = TARGETS[targetKey].envVar;
    throw new Error(
      [
        `FFmpeg bundle for ${targetKey} is incomplete.`,
        `Missing: ${missing.join(", ")}`,
        `Set ${envVar} to a directory containing ${TARGETS[targetKey].binaries.join(", ")}`,
        `or pre-populate ${targetDir(targetKey)} before packaging.`
      ].join(" ")
    );
  }

  return {
    ok: true,
    targetKey,
    sourceDir: sourceDir ? path.resolve(sourceDir) : null,
    targetDir: targetDir(targetKey)
  };
}

function archNameFromBuilderArch(arch) {
  if (typeof arch === "number") {
    return Arch[arch];
  }
  return String(arch);
}

function targetKeyFor(platformName, arch) {
  const archName = archNameFromBuilderArch(arch);
  const key = `${platformName}-${archName}`;
  if (TARGETS[key]) {
    return key;
  }

  if (platformName === "darwin" && archName === "universal") {
    return "darwin-universal";
  }

  return null;
}

async function beforePack(context) {
  const key = targetKeyFor(context.electronPlatformName, context.arch);
  if (!key) {
    return;
  }

  const result = stageBundle(key, { required: true });
  console.log(
    `[ffmpeg-bundle] ${result.targetKey} ready at ${result.targetDir}` +
      (result.sourceDir ? ` from ${result.sourceDir}` : "")
  );
}

function currentTargetKey() {
  if (process.platform === "darwin") {
    return process.arch === "arm64" ? "darwin-arm64" : "darwin-x64";
  }
  if (process.platform === "win32") {
    return process.arch === "arm64" ? "win32-arm64" : "win32-x64";
  }
  return null;
}

function runCli(args) {
  const targets = args.includes("--all")
    ? Object.keys(TARGETS)
    : args.filter((value) => !value.startsWith("--"));
  const resolvedTargets = targets.length > 0 ? targets : [currentTargetKey()].filter(Boolean);

  if (resolvedTargets.length === 0) {
    throw new Error("No supported default FFmpeg bundle target for this platform.");
  }

  const results = resolvedTargets.map((targetKey) => stageBundle(targetKey, { required: true }));
  for (const result of results) {
    console.log(
      `[ffmpeg-bundle] staged ${result.targetKey} at ${result.targetDir}` +
        (result.sourceDir ? ` from ${result.sourceDir}` : "")
    );
  }
}

if (require.main === module) {
  try {
    runCli(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

module.exports = {
  beforePack,
  stageBundle,
  targetKeyFor
};
