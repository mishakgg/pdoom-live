import { listTopics } from "@pdoom/db";
import Link from "next/link";
import { typeLabel } from "@/lib/format";
import { canonicalOrigin, listPageFields, pageMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return pageMetadata(canonicalOrigin(), listPageFields("topics"));
}

export default async function TopicsPage() {
  const topics = await listTopics();
  return (
    <>
      <h1>Topics</h1>
      <p className="lede">Definitions are part of the topic. Child questions under frontier AI risk are not rolled into one probability.</p>
      <div className="topic-list">
        {topics.map((topic) => (
          <article className="card" key={topic.slug}>
            <h2><Link href={`/topics/${topic.slug}`}>{topic.name}</Link></h2>
            <p>{topic.definition}</p>
            <p className="meta">
              version {topic.version}
              {topic.parent_slug ? ` · parent ${topic.parent_slug}` : ""}
              {" · "}
              {Object.entries(topic.statement_counts).map(([type, count]) => `${count} ${typeLabel(type)}`).join(" · ") || "no statements"}
            </p>
          </article>
        ))}
      </div>
    </>
  );
}
