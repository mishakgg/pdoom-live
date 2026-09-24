export const metadata = { title: "Methodology" };

export default function MethodologyPage() {
  return (
    <>
      <h1>Methodology</h1>
      <p className="lede">
        pdoom.live is a source-first observatory. The current deployment demonstrates the product with a synthetic fixture cohort. It does not describe real researchers and it is not a consensus.
      </p>
      <section className="panel">
        <h2>Three statement classes</h2>
        <p><strong>Explicit numerical estimate.</strong> The person supplied a number, range, or distribution. The question, unit, horizon, and condition are stored with it.</p>
        <p><strong>Explicit qualitative view.</strong> The person expressed a view without a number. The product does not invent a probability for that wording.</p>
        <p><strong>Model-inferred signal.</strong> A machine classification or synthesis. It is labeled as a model output and is not shown as the person’s probability.</p>
      </section>
      <section>
        <h2>What is not aggregated</h2>
        <p>Extinction, catastrophic harm, permanent disempowerment, and AGI arrival are different questions. A conditional probability is different from an unconditional one. A missing horizon stays missing. A range is not forced into a point. An unreviewed estimate stays out of a published distribution.</p>
        <p>The extinction distribution uses method <code>explicit-numeric-distribution/1.0.0</code>. It keeps the latest human-verified point estimate per cohort member for question key <code>ai_extinction_unconditional_by_2070</code> only. The median is the midpoint of the two central included values when the count is even. It is a summary of those records, not a belief of the cohort.</p>
        <p>Statement volume uses method <code>count-by-topic-type/1.0.0</code>. It counts records by topic and statement class. It does not average them.</p>
      </section>
      <section>
        <h2>Provenance</h2>
        <p>Each statement points at a person, a source item, and an evidence segment. Publication time and observation time are separate. Content is addressed by hash and a reference. List responses do not include unpublished source bodies. Source text is rendered as text.</p>
        <p>Identity links require an external namespace and identifier. Samir Okonkwo and Samira Okonkwo remain different people.</p>
      </section>
      <section>
        <h2>Coverage</h2>
        <p>The fixture cohort is versioned. People outside it, including the hostile-content persona, do not enter cohort trends. Missing estimates are counted as missing. Absence is not zero.</p>
      </section>
    </>
  );
}
