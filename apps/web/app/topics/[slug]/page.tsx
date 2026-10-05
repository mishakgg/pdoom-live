import { statementListQuerySchema } from "@pdoom/contracts";
import { listStatements } from "@pdoom/db";
import { InvalidFilters } from "@/components/filters";
import { HistoryPreview } from "@/components/history-preview";
import { JsonLd } from "@/components/json-ld";
import { StatementCard } from "@/components/statement-bits";
import { loadTopic } from "@/lib/loaders";
import { hasNarrowingFilters, researchFilters, statementsHref } from "@/lib/presentation";
import { requestNonce } from "@/lib/request-nonce";
import { canonicalOrigin, notFoundMetadata, pageMetadata, topicFields } from "@/lib/seo";
import { topicStructuredData } from "@/lib/structured-data";
import { QuestionHorizonList, StatementQuestionLine, distinctQuestions, statementFacts } from "../question-horizons";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const topic = await loadTopic(slug);
  if (!topic) return notFoundMetadata();
  return pageMetadata(canonicalOrigin(), topicFields(topic));
}

export default async function TopicPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const { slug } = await params;
  const query = await searchParams;
  const topic = await loadTopic(slug);
  if (!topic) notFound();
  const filters = { ...researchFilters(query), topic: slug };
  const narrowed = hasNarrowingFilters(filters, "topic");
  let statements = topic.statements;
  let total = topic.statement_total;
  let invalid = false;
  if (narrowed) {
    const parsed = statementListQuerySchema.safeParse({ ...filters, limit: 50, sort: "event_time_desc" });
    if (!parsed.success) invalid = true;
    else {
      const page = await listStatements(parsed.data);
      statements = page.data;
      total = page.page.total;
    }
  }
  const origin = canonicalOrigin();
  const nonce = await requestNonce();
  return (
    <>
      <JsonLd nonce={nonce} data={topicStructuredData({ origin, slug: topic.slug, name: topic.name, definition: topic.definition })} />
      <p className="kicker">Topic version {topic.version}</p>
      <h1>{topic.name}</h1>
      <p className="lede">{topic.definition}</p>
      <QuestionHorizonList
        topicDefinition={topic.definition}
        questions={distinctQuestions(statements.map((statement) => statementFacts(statement)))}
        includeTopicDefinition={false}
        emptyAsUnknown={statements.length === 0 && topic.statement_total === 0}
        partial={total > statements.length ? { shown: statements.length, total } : null}
      />
      {slug === "ai-extinction" ? (
        <p>
          A comparable distribution, when one exists, is limited to a single question key.{" "}
          <Link href="/trends/extinction-by-2070-distribution">Open the 2070 extinction distribution</Link>.
        </p>
      ) : null}
      {invalid ? <InvalidFilters /> : null}
      <section aria-labelledby="topic-statements">
        <h2 id="topic-statements">Statements</h2>
        <HistoryPreview
          shown={statements.length}
          total={total}
          href={statementsHref(filters)}
          note={narrowed
            ? `This view keeps the topic and the other selected filters. ${topic.statement_total} public ${topic.statement_total === 1 ? "statement uses" : "statements use"} this definition before those filters.`
            : null}
        />
        {statements.length ? statements.map((statement) => (
          <div key={statement.slug}>
            <StatementCard statement={statement} headingLevel="h3" filters={filters} />
            <StatementQuestionLine statement={statement} />
          </div>
        )) : narrowed || topic.statement_total > 0 ? (
          <p>No statement in this view matches the selected filters. {topic.statement_total} public {topic.statement_total === 1 ? "statement uses" : "statements use"} this definition before those filters.</p>
        ) : (
          <p>No statement has been collected under this topic. That is a coverage gap, not evidence that nobody has addressed the question.</p>
        )}
      </section>
    </>
  );
}
