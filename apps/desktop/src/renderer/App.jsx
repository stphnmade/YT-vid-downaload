import React, { useEffect, useRef, useState } from "react";
import {
  Download,
  FolderOpen,
  FileText,
  X,
  AlertTriangle
} from "lucide-react";

const TERMINAL_STATUSES = new Set(["completed", "error", "cancelled"]);

function formatStatus(status) {
  if (status === "downloading") {
    return "Downloading";
  }
  if (status === "processing") {
    return "Processing";
  }
  if (status === "completed") {
    return "Completed";
  }
  if (status === "cancelled") {
    return "Cancelled";
  }
  if (status === "error") {
    return "Failed";
  }
  return "Idle";
}

function App() {
  const [url, setUrl] = useState("");
  const [format, setFormat] = useState("mp4");
  const [savePath, setSavePath] = useState("");
  const [progress, setProgress] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const pollRef = useRef(null);

  const refreshHistory = async () => {
    const result = await window.ytApi.getHistory();
    if (result.ok) {
      setHistory(result.data.history || []);
    }
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const handleProgressUpdate = (data) => {
    if (!data || data.status === "idle") {
      return;
    }
    setProgress(data);
    if (TERMINAL_STATUSES.has(data.status)) {
      setIsBusy(false);
      stopPolling();
      refreshHistory();
    } else {
      setIsBusy(true);
    }
  };

  const startPolling = () => {
    if (pollRef.current) {
      return;
    }
    pollRef.current = setInterval(async () => {
      const result = await window.ytApi.getProgress();
      if (!result.ok) {
        setError(result.error);
        setIsBusy(false);
        stopPolling();
        return;
      }
      handleProgressUpdate(result.data);
    }, 600);
  };

  const loadInitial = async () => {
    const [settingsResult, historyResult, progressResult] = await Promise.all([
      window.ytApi.getSettings(),
      window.ytApi.getHistory(),
      window.ytApi.getProgress()
    ]);

    if (settingsResult.ok) {
      setSavePath(settingsResult.data.savePath);
    }

    if (historyResult.ok) {
      setHistory(historyResult.data.history || []);
    }

    if (progressResult.ok) {
      handleProgressUpdate(progressResult.data);
      if (
        progressResult.data &&
        !TERMINAL_STATUSES.has(progressResult.data.status) &&
        progressResult.data.status !== "idle"
      ) {
        startPolling();
      }
    }
  };

  useEffect(() => {
    loadInitial();
    return () => stopPolling();
  }, []);

  const handleDownload = async () => {
    if (!url.trim()) {
      setError("Paste a YouTube URL to start.");
      return;
    }
    setError("");
    setIsBusy(true);
    const result = await window.ytApi.startDownload({
      url,
      format,
      outputDir: savePath
    });

    if (!result.ok) {
      setError(result.error);
      setIsBusy(false);
      return;
    }

    setProgress(result.data.job);
    startPolling();
  };

  const handleCancel = async () => {
    const result = await window.ytApi.cancelDownload();
    if (!result.ok) {
      setError(result.error);
    }
  };

  const handleSelectFolder = async () => {
    const result = await window.ytApi.selectSavePath();
    if (!result.ok) {
      setError(result.error);
      return;
    }
    if (result.data && result.data.savePath) {
      setSavePath(result.data.savePath);
    }
  };

  const percent = progress ? Math.min(100, Math.max(0, progress.percent)) : 0;
  const statusLabel = progress ? formatStatus(progress.status) : "Idle";
  const filenameLabel = progress?.filename || progress?.title || "";

  return (
    <div className="app">
      <header className="hero">
        <p className="eyebrow">YT Download App</p>
        <h1>Bring it offline.</h1>
        <p className="subhead">
          Paste a YouTube link, choose MP4 or MP3, and save it to your Downloads
          folder.
        </p>
      </header>

      <section className="card">
        <div className="card-header">
          <div>
            <h2>Download</h2>
            <p>One link at a time. Calm, clear, and quick.</p>
          </div>
          <div className="format-toggle">
            <button
              type="button"
              className={format === "mp4" ? "active" : ""}
              onClick={() => setFormat("mp4")}
              disabled={isBusy}
            >
              MP4
            </button>
            <button
              type="button"
              className={format === "mp3" ? "active" : ""}
              onClick={() => setFormat("mp3")}
              disabled={isBusy}
            >
              MP3
            </button>
          </div>
        </div>

        <label className="field">
          <span>YouTube URL</span>
          <input
            type="text"
            placeholder="https://www.youtube.com/watch?v="
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            disabled={isBusy}
          />
        </label>

        <div className="path-row">
          <div>
            <span className="path-label">Save to</span>
            <p className="path-value">{savePath || "Loading..."}</p>
          </div>
          <button
            type="button"
            className="ghost"
            onClick={handleSelectFolder}
            disabled={isBusy}
          >
            Change folder
          </button>
        </div>

        {error ? (
          <div className="error">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        <div className="actions">
          <button
            type="button"
            className="primary"
            onClick={handleDownload}
            disabled={isBusy}
          >
            <Download size={18} />
            Download
          </button>
          <button
            type="button"
            className="secondary"
            onClick={handleCancel}
            disabled={!isBusy}
          >
            <X size={18} />
            Cancel
          </button>
        </div>

        <div className="progress">
          <div className="progress-top">
            <div>
              <p className="status">{statusLabel}</p>
              {filenameLabel ? <p className="filename">{filenameLabel}</p> : null}
            </div>
            <p className="percent">{percent}%</p>
          </div>
          <div className="bar">
            <span style={{ width: `${percent}%` }} />
          </div>
        </div>
      </section>

      <section className="card history">
        <div className="card-header">
          <div>
            <h2>Recent history</h2>
            <p>Latest downloads and errors.</p>
          </div>
        </div>

        <div className="history-list">
          {history.length === 0 ? (
            <p className="empty">No downloads yet.</p>
          ) : (
            history.map((item) => (
              <div className="history-item" key={item.id}>
                <div className="history-info">
                  <p className="history-title">
                    {item.title || item.filename || item.url}
                  </p>
                  <p className="history-meta">
                    {formatStatus(item.status)} · {item.format?.toUpperCase()}
                  </p>
                  {item.error ? (
                    <p className="history-error">{item.error}</p>
                  ) : null}
                </div>
                <div className="history-actions">
                  {item.filepath && item.status === "completed" ? (
                    <>
                      <button
                        type="button"
                        className="icon"
                        onClick={() => window.ytApi.openFile(item.filepath)}
                        title="Open file"
                      >
                        <FileText size={18} />
                      </button>
                      <button
                        type="button"
                        className="icon"
                        onClick={() => window.ytApi.openFolder(item.filepath)}
                        title="Open folder"
                      >
                        <FolderOpen size={18} />
                      </button>
                    </>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

export default App;
