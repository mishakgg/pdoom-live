import { JsonLd } from "@/components/json-ld";
import { StatementCard } from "@/components/statement-bits";
import { loadTopic } from "@/lib/loaders";
import { canonicalOrigin, notFoundMetadata, pageMetadata, topicFields } from "@/lib/seo";
import { topicStructuredData } from "@/lib/structured-data";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const topic = await loadTopic(slug);
  if (!topic) return notFoundMetadata();
  return pageMetadata(canonicalOrigin(), topicFields(topic));
}

export default async function TopicPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const topic = await loadTopic(slug);
  if (!topic) notFound();
  const origin = canonicalOrigin();
  return (
    <>
      <JsonLd data={topicStructuredData({ origin, slug: topic.slug, name: topic.name, definition: topic.definition })} />
      <p className="kicker">Topic version {topic.version}</p>
      <h1>{topic.name}</h1>
      <p className="lede">{topic.definition}</p>
      {slug === "frontier-ai-risk" ? (
        <p className="warning">Statements under this family use different questions. They are not aggregated into one p(doom).</p>
      ) : null}
      {slug === "ai-extinction" ? (
        <p>
          A comparable distribution, when one exists, is limited to a single question key.{" "}
          <Link href="/trends/extinction-by-2070-distribution">Open the 2070 extinction distribution</Link>.
        </p>
      ) : null}
      {topic.statements.map((statement) => (
        <StatementCard key={statement.slug} statement={statement} />
      ))}
    </>
  );
}
