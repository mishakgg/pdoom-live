import Link from "next/link";

export const metadata = { title: "Methodology" };

// A prerendered document cannot carry the per-request CSP nonce.
export const dynamic = "force-dynamic";

export default function MethodologyPage() {
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
        <h2>Question keys stay separate</h2>
        <p>The comparability boundary is <code>question_key</code>. Unconditional extinction, conditional extinction, catastrophic harm, permanent disempowerment, AGI probabilities, AGI years, ASI years, coding automation, unemployment, productivity, and GDP growth each keep their own key. A shared topic is not a reason to average them.</p>
        <p>Probability distributions use method <code>explicit-numeric-distribution/1.1.0</code>. They keep the latest human-verified point estimate per person for one question key, one unit, and one conditionality. A median is the midpoint of the two central values when the count is even, and it appears from 3 included point estimates upward. Below that, the page lists the individual estimates. Ranges stay out of the median and are not converted into midpoints. An earlier estimate is marked superseded only when a human-verified update or retraction links it to a later estimate. A later timestamp alone is an omission from the cross-section, not a revision.</p>
        <p>Timeline forecasts use method <code>timeline-forecast/1.0.0</code>. The value is a year. A predicted year stays a date. Probability-of-arrival questions stay on the probability method.</p>
        <p>Quantity forecasts use method <code>quantity-forecast/1.0.0</code>. The unit has to match before any summary. A share, a job count, percentage points, and a probability are different units. Productivity and GDP can share a unit and still stay apart when their question keys differ.</p>
        <p>Historical revisions use method <code>historical-revision/1.0.0</code>. A line is drawn only along a human-verified update or retraction between two explicit estimates of the same question. A repeat is labeled as a repeat. Two numbers from the same person, with no verified link, stay unlinked.</p>
        <p>Statement volume uses method <code>count-by-topic-type/1.0.0</code>. It counts records by topic and statement class.</p>
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
        <p>The public research export and <Link href="/data">/data</Link> API omit rejected, unreviewed, and needs-review records. Machine-validated rows stay labeled as machine output.</p>
      </section>
    </>
  );
}
