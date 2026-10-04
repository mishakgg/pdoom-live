import { getDatasetStamp } from "@pdoom/db";

/** Shown on every rendered page when the current dataset is a fixture. */
export async function DatasetNotice() {
  let kind: string | null = null;
  try {
    kind = (await getDatasetStamp()).dataset_kind;
  } catch {
    return null;
  }
  if (kind !== "synthetic") return null;
  return (
    <p className="dataset-banner" role="status">
      <strong>Synthetic demo data.</strong> The loaded dataset is a synthetic fixture. People, organizations, and quotations here are fictional.
    </p>
  );
}
