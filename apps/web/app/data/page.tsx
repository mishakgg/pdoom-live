import { getPublicCatalog } from "@pdoom/db";
import Link from "next/link";
import { formatWhen } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Data",
  description: "Public dataset exports, cohort, methodology, and the versioned read API for pdoom.live.",
};

const files = [
  ["manifest.json", "Dataset version, cohort, methodology, counts, license, and file hashes"],
  ["people.json / people.csv", "Tracked people and current public affiliation"],
  ["organizations.json", "Organizations referenced by public records"],
  ["identities.json", "Public external identities"],
  ["sources.json", "Public sources"],
  ["source_items.json", "Source items that back a public statement"],
  ["statements.json / statements.csv", "Public statements with provenance"],
  ["forecasts.json / forecasts.csv", "Forecasts with question, definition, horizon, and unit"],
  ["topics.json", "Topic definitions and versions"],
  ["relationships.json", "Public statement relationships"],
  ["trends.json", "Published trend definitions and observations"],
];

export default async function DataPage() {
  const catalog = await getPublicCatalog(null);
  const dataset = catalog.dataset;
  const citation = dataset
    ? `pdoom.live public dataset ${dataset.dataset_id}, cohort ${catalog.cohort?.slug ?? "unknown"} ${catalog.cohort?.version ?? ""}, API v1, export schema ${catalog.export_schema_version}. ${dataset.imported_at ?? "import time unknown"}. https://pdoom.live/data`
    : "pdoom.live public dataset, API v1. https://pdoom.live/data";
  return (
    <>
      <h1>Public data</h1>
      <p className="lede">
        The read API and bulk snapshot are a research export of records already eligible for the public dataset. They are not the internal canonical import, and they do not include rejected, unreviewed, or needs-review material.
      </p>
      <p className="fresh">
        <span><strong>{dataset?.dataset_kind === "synthetic" ? "Synthetic fixture" : "Live dataset"}</strong> {dataset?.dataset_id ?? "No dataset loaded"}</span>
        <span>Cohort {catalog.cohort?.name ?? "none"} {catalog.cohort?.version ?? ""}</span>
        <span>Imported {formatWhen(dataset?.imported_at)}</span>
        <span>Latest observation {formatWhen(catalog.latest_observed_at)}</span>
        <span>{catalog.counts.statements} public statements</span>
      </p>
      <section className="panel">
        <h2>What is in the export</h2>
        <p>{dataset?.notice ?? "No dataset is loaded."}</p>
        <p>
          Included review states: {catalog.publication.included_review_states.join(", ")}. A machine-validated record stays labeled as machine output and is not human-verified. {catalog.publication.site_difference}
        </p>
        <p className="meta">
          {catalog.counts.people} people · {catalog.counts.organizations} organizations · {catalog.counts.identities} identities · {catalog.counts.sources} sources · {catalog.counts.source_items} source items · {catalog.counts.forecasts} forecasts · {catalog.counts.topics} topics · {catalog.counts.relationships} relationships · {catalog.counts.trends} trends
        </p>
      </section>
      <section>
        <h2>API</h2>
        <p>
          Stable reads are under <Link href="/api/v1/dataset"><code>/api/v1</code></Link>. The machine-readable description is <Link href="/api/v1/openapi.json">OpenAPI</Link>. Unversioned <code>/api/*</code> routes are the application query API and are not a stability promise.
        </p>
        <ul>
          <li><Link href="/api/v1/people">/api/v1/people</Link> and <code>/api/v1/people/{"{slug}"}</code></li>
          <li><Link href="/api/v1/statements">/api/v1/statements</Link> and <code>/api/v1/statements/{"{slug}"}</code></li>
          <li><Link href="/api/v1/topics">/api/v1/topics</Link></li>
          <li><Link href="/api/v1/sources">/api/v1/sources</Link></li>
          <li><Link href="/api/v1/trends">/api/v1/trends</Link></li>
          <li><code>/api/v1/search?q=</code></li>
        </ul>
        <p>Pages use opaque cursors. <code>limit</code> is 1–50. Search text is 2–120 characters. Responses send <code>ETag</code>, <code>Cache-Control</code>, and <code>Last-Modified</code> from the dataset import time.</p>
      </section>
      <section>
        <h2>Bulk snapshot</h2>
        <p>An operator generates files without overwriting source data:</p>
        <p><code>npm run data:export -- --out data/exports/public --generated-at 2026-09-27T00:00:00.000Z</code></p>
        <p>The same timestamp and the same imported dataset reproduce the same snapshot id. <code>data/exports/</code> is generated output.</p>
        <table className="dist">
          <thead>
            <tr><th>File</th><th>Contents</th></tr>
          </thead>
          <tbody>
            {files.map(([file, description]) => (
              <tr key={file}><td><code>{file}</code></td><td>{description}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
      <section>
        <h2>Cohort and methodology</h2>
        <p>{catalog.cohort?.definition ?? "No cohort is loaded."}</p>
        <p>
          Written cohort methodology {catalog.methodology.cohort_methodology_version} ({catalog.methodology.cohort_methodology_ref}). {catalog.methodology.cohort_methodology_note}
        </p>
        <p>Trend methods: {catalog.methodology.trend_method_versions.join(", ") || "none published"}.</p>
        <p>
          Provenance rules: {catalog.methodology.provenance_policy_ref}. Statement classes and aggregation rules are on the <Link href="/methodology">methodology page</Link>.
        </p>
      </section>
      <section>
        <h2>License and citation</h2>
        <p><strong>{catalog.license.status === "cc0-1.0" ? "CC0 1.0 for this synthetic fixture export." : "Live redistribution license: pending."}</strong> {catalog.license.note}</p>
        <p>Cite the dataset, not a chart:</p>
        <p className="meta">{citation}</p>
      </section>
      <section>
        <h2>Limitations</h2>
        <p>This is not a census of AI researchers and not a consensus. Absence of an estimate is not zero. Extinction, catastrophic harm, disempowerment, and AGI arrival stay separate questions. A number is stored only when the person supplied one, and it keeps its definition, horizon, and conditions. Qualitative views and model-inferred signals are not converted into probabilities.</p>
        <p>Exports contain short evidence excerpts, not full articles or transcripts. Operational extraction notes, curator notes, and unpublished review queues are omitted.</p>
      </section>
    </>
  );
}
