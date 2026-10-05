import { listStatements, listTopics } from "@pdoom/db";
import Link from "next/link";
import { EmptyState } from "@/components/states";
import { typeLabel } from "@/lib/format";
import { canonicalOrigin, listPageFields, pageMetadata } from "@/lib/seo";
import { QuestionHorizonList, SEPARATE_QUESTIONS, distinctQuestions, statementFacts } from "./question-horizons";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  return pageMetadata(canonicalOrigin(), listPageFields("topics"));
}

export default async function TopicsPage() {
  const topics = await listTopics();
  const loaded = await Promise.all(topics.map(async (topic) => {
    const page = await listStatements({ topic: topic.slug, limit: 50, sort: "event_time_desc" });
    return {
      topic,
      questions: distinctQuestions(page.data.map((statement) => statementFacts(statement))),
      shown: page.data.length,
      total: page.page.total,
    };
  }));
  return (
    <>
      <h1>Topics</h1>
      <p className="lede">{SEPARATE_QUESTIONS} Each topic keeps the question definition and the time horizon stored with its statements.</p>
      {loaded.length ? (
        <div className="topic-list">
          {loaded.map(({ topic, questions, shown, total }) => (
            <article className="card" key={topic.slug}>
              <h2><Link href={`/topics/${topic.slug}`}>{topic.name}</Link></h2>
              <QuestionHorizonList
                topicDefinition={topic.definition}
                questions={questions}
                headingLevel="h3"
                headingId={`question-horizons-${topic.slug}`}
                notice={false}
                partial={total > shown ? { shown, total } : null}
              />
              <p className="meta">
                Version {topic.version}
                {topic.parent_slug ? ` · parent ${topic.parent_slug}` : ""}
                {" · "}
                {Object.entries(topic.statement_counts).map(([type, count]) => `${count} ${typeLabel(type)}`).join(" · ") || "No statement collected"}
              </p>
              <p><Link href={`/statements?topic=${topic.slug}`}>All statements on this question</Link></p>
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
