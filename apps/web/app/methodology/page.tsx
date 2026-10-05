import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import { requestNonce } from "@/lib/request-nonce";
import { canonicalOrigin, listPageFields, pageMetadata } from "@/lib/seo";
import { methodologyStructuredData } from "@/lib/structured-data";

export async function generateMetadata() {
  return pageMetadata(canonicalOrigin(), listPageFields("methodology"));
}

export const dynamic = "force-dynamic";

export default async function MethodologyPage() {
  const nonce = await requestNonce();
  return (
    <>
      <JsonLd nonce={nonce} data={methodologyStructuredData(canonicalOrigin(), null)} />
      <MethodologyDocument />
    </>
  );
}

export function MethodologyDocument() {
  return (
    <>
      <h1>Methodology</h1>
      <p className="lede">
        pdoom.live is a source-first observatory. A synthetic fixture is labeled synthetic and does not describe real researchers. A live dataset names its cohort and version. It is not a consensus.
      </p>
      <section className="panel">
        <h2>Three statement classes</h2>
        <p><strong>Explicit numerical estimate.</strong> The person supplied a number, range, or distribution. The question, unit, horizon, and condition are stored with it.</p>
        <p><strong>Explicit qualitative view.</strong> The person expressed a view without a number. The product does not invent a probability for that wording.</p>
        <p><strong>Model-inferred signal.</strong> A machine classification or synthesis. It is labeled as a model output and is not shown as the person’s probability.</p>
      </section>
      <section>
        <h2>Exact questions stay separate</h2>
        <p>A stored <code>question_key</code> can name a broad family or an exact comparison. Families such as unconditional extinction, conditional extinction, catastrophic harm, permanent disempowerment, AGI arrival, coding automation, unemployment, productivity, and GDP growth are not averaged together. A family record joins an exact question only when the outcome, condition, deadline, and unit agree. An unknown or ambiguous record stays listed on its own, with the reason it was not pooled. A shared topic is not a reason to average them.</p>
        <p>A probability&apos;s deadline is part of the question. One person&apos;s probability by 2030 and probability by 2050 stay different questions. A predicted arrival year is the forecasted value, so different predicted years can sit in one arrival-year comparison. Ranges, bounds, and quantiles stay as supplied. They are not converted into midpoints.</p>
        <p>Prepared probability distributions use method <code>explicit-numeric-distribution/1.2.0</code>. A published trend definition keeps the method version stored with that definition. The pooling rules actually applied are <code>comparability/1.0.0</code>. Each cross-section keeps the latest human-verified point estimate per person for one exact question. A median is the midpoint of the two central values when the count is even, and it appears from 3 included point estimates upward. Below that, the page lists the individual estimates. The median summarizes the included statements. It is not automatically the probability of the event. An earlier estimate is marked superseded only when a human-verified update or retraction links it to a later eligible estimate. A later timestamp alone is an omission from the cross-section, not a revision. A verified withdrawal does not need a replacement number.</p>
        <p>Prepared timeline forecasts use method <code>timeline-forecast/1.1.0</code>. The value is a year. A predicted year stays a date. Probability-of-arrival questions stay on the probability method.</p>
        <p>Prepared quantity forecasts use method <code>quantity-forecast/1.1.0</code>. The unit has to match before any summary. A share, a job count, percentage points, and a probability are different units. Productivity and GDP can share a unit and still stay apart when the outcome differs.</p>
        <p>Prepared historical revisions use method <code>historical-revision/1.1.0</code>. A line is drawn only along a human-verified update, retraction, or withdrawal between statements of the same exact question by the same person. A repeat, a clarification, and a contradiction stay off the change chart. A machine-suggested link is not a verified change of mind. Two numbers from the same person, with no verified link, stay unlinked.</p>
        <p>Qualitative statements use method <code>qualitative-statements/1.0.0</code>. They are listed without a probability. Records that cannot be pooled use method <code>unpooled-inspection/1.0.0</code>.</p>
        <p>Statement volume uses method <code>count-by-topic-type/1.0.0</code>. It counts records by topic and statement class.</p>
        <p>A calculation time is the time the current corpus was read. It is not a reconstruction of what was known on an earlier date. A historical reconstruction requires the statement date, the observation time, and the human review time to all fall on or before the cutoff. Public scoring of resolved forecasts stays off until an adequate resolved dataset exists. An unresolved extinction forecast is not a failure.</p>
        <p>Every view names the cohort, the method version, the contributing people and statements, the missing members, and the question. A handful of estimates is a handful of estimates. Public numeric views accept <code>human_verified</code> records. The full rules are in the trend methodology note.</p>
      </section>
      <section>
        <h2>Provenance</h2>
        <p>Each statement points at a person, a source item, and an evidence segment. Publication time and observation time are separate. Content is addressed by hash and a reference. List responses do not include unpublished source bodies. Source text is rendered as text.</p>
        <p><code>human_verified</code> means a person reviewed the evidence. An extractor can leave a record <code>unreviewed</code>, <code>needs_review</code>, or <code>machine_validated</code>. It cannot promote a record to <code>human_verified</code>. Unreviewed and rejected records stay off the public pages. Needs-review records are not shown as verified.</p>
        <p>Identity links require an external namespace and identifier. Samir Okonkwo and Samira Okonkwo remain different people.</p>
      </section>
      <section>
        <h2>Coverage and freshness</h2>
        <p>Coverage counts the loaded cohort: people with sources, people with a non-academic source, people with a first-party channel, and people with a public statement. An academic-works feed is not complete coverage.</p>
        <p>Freshness describes collection, not whether a person has spoken. A source is current when its last successful check is within 14 days, aging within 90 days, stale after that, and never checked when no success time is stored.</p>
        <p>People outside the loaded cohort do not enter that cohort&apos;s trends. Missing estimates are counted as missing. Absence is not zero.</p>
        <p>A person with no collected statement is missing from the record. That absence is not evidence they have never spoken. A live dataset with zero human-verified statements withholds published trends until a statement is human verified. Machine-validated records stay labeled as model output.</p>
        <p>The public research export and <Link href="/data">/data</Link> API omit rejected, unreviewed, and needs-review records. Machine-validated rows stay labeled as machine output.</p>
      </section>
    </>
  );
}
