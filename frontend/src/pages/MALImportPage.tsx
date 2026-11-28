import { useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { useMALImport } from "../api/useMALImport";
import type { MALImportResponse } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { Upload, X } from "lucide-react";
import { PageTitle } from "../components/PageTitle";
import "../styles/import.css";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ".xml,.gz,.xml.gz";
const MAL_EXPORT_URL = "https://myanimelist.net/panel.php?go=export";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isAcceptedFile(file: File) {
  return /\.(xml|xml\.gz|gz)$/i.test(file.name);
}

export function MALImportPage() {
  const { user, authLoading } = useAuth();
  const fileInput = useRef<HTMLInputElement>(null);
  const mutation = useMALImport();
  const [file, setFile] = useState<File | null>(null);
  const [summary, setSummary] = useState<MALImportResponse | null>(null);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  if (authLoading)
    return (
      <section className="browse-page">
        <p>Checking your account…</p>
      </section>
    );
  if (!user)
    return (
      <Navigate replace to={`/login?next=${encodeURIComponent("/import")}`} />
    );

  function chooseFile(candidate?: File) {
    if (!candidate) return;
    setError("");
    setSummary(null);
    setCompleted(false);
    mutation.reset();
    if (!isAcceptedFile(candidate)) {
      setFile(null);
      setError("Choose a MyAnimeList export file (.xml, .xml.gz, or .gz).");
      return;
    }
    if (candidate.size > MAX_FILE_SIZE) {
      setFile(null);
      setError("This file is larger than 5 MB. Choose a smaller export file.");
      return;
    }
    setFile(candidate);
  }

  async function submit(dryRun: boolean) {
    if (!file) return;
    setError("");
    try {
      const result = await mutation.mutateAsync({ file, dryRun });
      if (dryRun) setSummary(result);
      else {
        setSummary(result);
        setCompleted(true);
      }
    } catch (reason) {
      setError(
        getErrorMessage(reason, "Could not import your MyAnimeList file.")
      );
    }
  }

  function reset() {
    setFile(null);
    setSummary(null);
    setCompleted(false);
    setError("");
    mutation.reset();
    if (fileInput.current) fileInput.current.value = "";
  }

  const fileChip = file && (
    <div className="import-file-chip">
      <span className="import-file-name">{file.name}</span>
      <span className="import-file-size">{formatSize(file.size)}</span>
      <button
        aria-label="Remove file"
        className="import-file-remove"
        onClick={reset}
        type="button"
      >
        <X aria-hidden="true" size={18} />
      </button>
    </div>
  );

  return (
    <section className="browse-page import-page">
      <header className="page-header">
        <div>
          <PageTitle lead="Import from MyAnimeList" />
          <p className="page-subtitle">
            Bring your watch history into AniMatch. Nothing is added until you
            confirm.
          </p>
        </div>
      </header>
      <div className="import-top">
        <aside className="import-guide" aria-labelledby="import-guide-title">
          <h2 className="sr-only" id="import-guide-title">
            Getting your export file
          </h2>
          <ol className="import-steps">
            <li>
              <span aria-hidden="true" className="import-step-marker">
                1
              </span>
              <div>
                <p className="import-step-title">Open MyAnimeList</p>
                <p className="muted">Sign in and go to your profile.</p>
              </div>
            </li>
            <li>
              <span aria-hidden="true" className="import-step-marker">
                2
              </span>
              <div>
                <p className="import-step-title">Choose Export My List</p>
                <p className="muted">
                  Pick Anime as the list type, then export.
                </p>
              </div>
            </li>
            <li>
              <span aria-hidden="true" className="import-step-marker">
                3
              </span>
              <div>
                <p className="import-step-title">Upload it here</p>
                <p className="muted">
                  Drop the file in the box, no need to unzip it.
                </p>
              </div>
            </li>
          </ol>
          <a
            className="secondary-action import-open-mal"
            href={MAL_EXPORT_URL}
            rel="noopener noreferrer"
            target="_blank"
          >
            Open MyAnimeList
          </a>
          <p className="import-mature-note muted">
            Imported 18+ titles stay hidden unless the 18+ toggle is on.
          </p>
        </aside>
        {!summary && !completed && (
          <div
            aria-label="Choose a MyAnimeList export file"
            className={`import-drop-zone${dragging ? " is-dragging" : ""}`}
            onDragEnter={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              chooseFile(event.dataTransfer.files[0]);
            }}
          >
            <input
              accept={ACCEPTED_TYPES}
              aria-label="MyAnimeList export file"
              className="sr-only"
              id="mal-file"
              onChange={(event) => chooseFile(event.currentTarget.files?.[0])}
              ref={fileInput}
              type="file"
            />
            <span aria-hidden="true" className="import-drop-icon">
              <Upload size={40} strokeWidth={1.4} />
            </span>
            <p className="import-drop-title">Drop your export file here</p>
            <p className="import-drop-description">
              Accepts .xml, .xml.gz or .gz files up to 5 MB.
            </p>
            <label
              className="secondary-action import-file-button"
              htmlFor="mal-file"
            >
              Choose a file
            </label>
          </div>
        )}
      </div>
      <div className="import-below">
        {!completed && !summary && file && (
          <>
            {fileChip}
            <div className="import-actions">
              <button
                className="primary-action"
                disabled={mutation.isPending}
                onClick={() => void submit(true)}
                type="button"
              >
                {mutation.isPending ? "Checking file…" : "Preview import"}
              </button>
              <p className="muted">Nothing is added until you confirm.</p>
            </div>
          </>
        )}
        {!completed && summary && (
          <div aria-live="polite" className="import-preview">
            <div className="import-preview-head">
              <h2 className="import-heading">Import preview</h2>
              {fileChip}
            </div>
            <dl className="import-stats">
              <div>
                <dt>Total entries</dt>
                <dd>{summary.total_entries}</dd>
              </div>
              <div className="is-highlight">
                <dt>To import</dt>
                <dd>{summary.to_import}</dd>
              </div>
              <div>
                <dt>Already on your list (skipped)</dt>
                <dd>{summary.skipped_existing}</dd>
              </div>
              <div>
                <dt>Not in our catalog</dt>
                <dd>{summary.unmatched_count}</dd>
              </div>
            </dl>
            {summary.unmatched.length > 0 && (
              <details className="import-unmatched">
                <summary>Unmatched titles ({summary.unmatched_count})</summary>
                <ul>
                  {summary.unmatched.map((entry, index) => (
                    <li key={`${entry.title}-${index}`}>{entry.title}</li>
                  ))}
                </ul>
              </details>
            )}
            <div className="import-confirm">
              <button
                className="secondary-action"
                onClick={reset}
                type="button"
              >
                Choose another file
              </button>
              <div className="import-confirm-primary">
                <button
                  className="primary-action"
                  disabled={mutation.isPending}
                  onClick={() => void submit(false)}
                  type="button"
                >
                  {mutation.isPending
                    ? "Importing…"
                    : `Import ${summary.to_import} ${
                        summary.to_import === 1 ? "title" : "titles"
                      }`}
                </button>
                <p className="muted">Nothing is added until you confirm.</p>
              </div>
            </div>
          </div>
        )}
        {error && (
          <p
            aria-live="assertive"
            className="form-error import-error"
            role="alert"
          >
            {error}
          </p>
        )}
        {completed && summary && (
          <div aria-live="polite" className="import-complete">
            <h2 className="import-heading">Import complete</h2>
            <p className="muted">
              Added {summary.to_import} titles. {summary.skipped_existing}{" "}
              already on your list were skipped, and {summary.unmatched_count}{" "}
              were not found in our catalog.
            </p>
            <nav aria-label="After import" className="import-actions">
              <Link className="primary-action" to="/list">
                My list
              </Link>
              <Link className="secondary-action" to="/for-you">
                For you
              </Link>
              <button className="text-button" onClick={reset} type="button">
                Choose another file
              </button>
            </nav>
          </div>
        )}
      </div>
      {error && <span className="sr-only">{error}</span>}
    </section>
  );
}
