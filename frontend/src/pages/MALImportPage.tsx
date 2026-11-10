import { useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { useMALImport } from "../api/useMALImport";
import type { MALImportResponse } from "../api/types";
import { useAuth } from "../auth/useAuth";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ".xml,.gz,.xml.gz";

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

  if (authLoading) return <section className="browse-page"><p>Checking your account…</p></section>;
  if (!user) return <Navigate replace to={`/login?next=${encodeURIComponent("/import")}`} />;

  function chooseFile(candidate?: File) {
    if (!candidate) return;
    setError(""); setSummary(null); setCompleted(false); mutation.reset();
    if (!isAcceptedFile(candidate)) { setFile(null); setError("Choose a MyAnimeList export file (.xml, .xml.gz, or .gz)."); return; }
    if (candidate.size > MAX_FILE_SIZE) { setFile(null); setError("This file is larger than 5 MB. Choose a smaller export file."); return; }
    setFile(candidate);
  }

  async function submit(dryRun: boolean) {
    if (!file) return;
    setError("");
    try {
      const result = await mutation.mutateAsync({ file, dryRun });
      if (dryRun) setSummary(result);
      else { setSummary(result); setCompleted(true); }
    } catch (reason) {
      setError(getErrorMessage(reason, "Could not import your MyAnimeList file."));
    }
  }

  function reset() {
    setFile(null); setSummary(null); setCompleted(false); setError(""); mutation.reset();
    if (fileInput.current) fileInput.current.value = "";
  }

  return <section className="browse-page mal-import-page">
    <header className="mal-import-heading"><p className="eyebrow">MyAnimeList</p><h1 className="page-title">Import your list</h1>
      <p>In MyAnimeList, open your profile, choose <strong>Export My List</strong>, and upload the .xml.gz or .xml file.</p>
    </header>
    {!completed && <>
      {!summary && <div aria-label="Choose a MyAnimeList export file" className={`mal-drop-zone${dragging ? " is-dragging" : ""}`} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]); }}>
        <input accept={ACCEPTED_TYPES} aria-label="MyAnimeList export file" className="sr-only" id="mal-file" onChange={(event) => chooseFile(event.currentTarget.files?.[0])} ref={fileInput} type="file" />
        <p className="mal-drop-title">Drop your export file here</p><p className="mal-drop-description">Accepted files: .xml, .xml.gz, .gz · Up to 5 MB</p>
        <label className="secondary-action mal-file-button" htmlFor="mal-file">Choose file</label>
        {file && <p className="mal-selected-file">Selected: {file.name}</p>}
      </div>}
      {summary && <div aria-live="polite" className="mal-import-summary">
        <h2>Import preview</h2>
        <dl className="mal-summary-grid"><div><dt>Total entries</dt><dd>{summary.total_entries}</dd></div><div><dt>To import</dt><dd>{summary.to_import}</dd></div><div><dt>Already on your list (skipped)</dt><dd>{summary.skipped_existing}</dd></div><div><dt>Not in our catalog</dt><dd>{summary.unmatched_count}</dd></div></dl>
        {summary.unmatched.length > 0 && <details className="mal-unmatched"><summary>Unmatched titles ({summary.unmatched_count})</summary><ul>{summary.unmatched.map((entry, index) => <li key={`${entry.title}-${index}`}>{entry.title}</li>)}</ul></details>}
        <p className="mal-mature-note">Imported titles that are 18+ stay hidden unless the 18+ toggle is on.</p>
      </div>}
      {error && <p aria-live="assertive" className="mal-import-error" role="alert">{error}</p>}
      {file && !summary && <button className="primary-action" disabled={mutation.isPending} onClick={() => void submit(true)} type="button">{mutation.isPending ? "Checking file…" : "Preview import"}</button>}
      {summary && <div className="mal-import-actions"><button className="primary-action" disabled={mutation.isPending} onClick={() => void submit(false)} type="button">{mutation.isPending ? "Importing…" : "Confirm import"}</button><button className="text-button" onClick={reset} type="button">Choose another file</button></div>}
    </>}
    {completed && summary && <div aria-live="polite" className="mal-import-summary status-success">
      <h2>Import complete</h2><p>Added {summary.to_import} titles. {summary.skipped_existing} already on your list and were skipped; {summary.unmatched_count} were not found in our catalog.</p>
      <nav aria-label="After import" className="mal-import-actions"><Link className="primary-action" to="/list">My list</Link><Link className="secondary-action" to="/for-you">For you</Link></nav>
      <button className="text-button" onClick={reset} type="button">Choose another file</button>
    </div>}
    {error && <span className="sr-only">{error}</span>}
  </section>;
}
