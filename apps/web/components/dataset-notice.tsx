import { connection } from "next/server";
import { loadDataset } from "@/lib/loaders";

/** Keep dataset context visible even when a visitor opens an audit URL directly. */
export async function DatasetNotice() {
  // The dataset belongs to this request, never to the build or a static shell.
  await connection();
  let dataset;
  try {
    dataset = await loadDataset();
  } catch {
    // Do not replace the page's own error boundary with a layout failure.
    return (
      <aside className="dataset-notice" role="status">
        Dataset status is unavailable. Reload before relying on these records.
      </aside>
    );
  }
  if (dataset?.dataset_kind !== "synthetic") return null;
  return (
    <aside className="dataset-notice" role="note" aria-label="Synthetic dataset notice">
      <strong>Synthetic fixture dataset.</strong>{" "}
      People, organizations, statements, and evidence are fictional. These records do not describe real researchers.
    </aside>
  );
}
