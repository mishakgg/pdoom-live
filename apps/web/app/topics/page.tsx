import { listTopics } from "@pdoom/db";
import Link from "next/link";
import { EmptyState } from "@/components/states";
import { typeLabel } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Topics" };

export default async function TopicsPage() {
  const topics = await listTopics();
  return (
    <>
      <h1>Topics</h1>
      <p className="lede">Definitions are part of the topic. Child questions under frontier AI risk are not rolled into one probability.</p>
      {topics.length ? (
        <div className="topic-list">
          {topics.map((topic) => (
            <article className="card" key={topic.slug}>
              <h2><Link href={`/topics/${topic.slug}`}>{topic.name}</Link></h2>
              <p>{topic.definition}</p>
              <p className="meta">
                Version {topic.version}
                {topic.parent_slug ? ` · parent ${topic.parent_slug}` : ""}
                {" · "}
                {Object.entries(topic.statement_counts).map(([type, count]) => `${count} ${typeLabel(type)}`).join(" · ") || "No statement collected"}
              </p>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="No topics are loaded">
          <p>The topic list is empty. Definitions have not been imported. That is not a map of the field.</p>
        </EmptyState>
      )}
    </>
  );
}
