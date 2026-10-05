import { classifyForecast, classifyQuestionKey, parseDeadline, type ForecastFacts } from "@pdoom/contracts";

/**
 * Extinction, catastrophic harm, disempowerment, AGI arrival, and economic
 * impact are different questions. Topic pages list each definition and horizon
 * on its own and do not calculate a probability from them.
 */
export const SEPARATE_QUESTIONS =
  "Extinction, catastrophic harm, disempowerment, AGI arrival, and economic impact each keep a separate definition and time horizon.";

export type QuestionSource = {
  forecast?: (ForecastFacts & { question_key?: string | null }) | null;
};

export type DisplayedQuestion = {
  id: string;
  question_key: string | null;
  question_text: string | null;
  definition: string | null;
  horizon: string;
  outcome_id: string;
};

function hasClassifierFacts(facts: ForecastFacts): boolean {
  return Boolean(
    facts.question_key ||
      facts.unit ||
      facts.value_type ||
      facts.forecast_kind ||
      facts.definition_text ||
      facts.question_text ||
      facts.condition_text,
  );
}

/**
 * A stored horizon is shown as stored.
 * A missing horizon uses the comparability field names already on the record:
 * `ambiguous` when the deadline status or exclusion is ambiguous, otherwise `unknown`.
 * A catalog deadline is not copied in to fill an empty horizon.
 */
export function horizonLabel(facts: ForecastFacts): string {
  const parsed = parseDeadline(facts);
  if (parsed.status === "ambiguous") return "ambiguous";
  const text = facts.horizon_text?.trim() ?? "";
  if (text) return text;
  if (parsed.status === "structured" && parsed.label) return parsed.label;
  if (hasClassifierFacts(facts) && classifyForecast(facts).reason === "ambiguous_horizon") return "ambiguous";
  return "unknown";
}

export function statementFacts(statement: QuestionSource): ForecastFacts {
  const forecast = statement.forecast;
  if (!forecast) return {};
  return {
    question_key: forecast.question_key ?? null,
    question_text: forecast.question_text ?? null,
    definition_text: forecast.definition_text ?? null,
    condition_text: forecast.condition_text ?? null,
    horizon_text: forecast.horizon_text ?? null,
    target_date_start: forecast.target_date_start ?? null,
    target_date_end: forecast.target_date_end ?? null,
    unit: forecast.unit ?? null,
    forecast_kind: forecast.forecast_kind ?? null,
    value_type: forecast.value_type ?? null,
    value_numeric: forecast.value_numeric ?? null,
    value_min: forecast.value_min ?? null,
    value_max: forecast.value_max ?? null,
    value_text: forecast.value_text ?? null,
    distribution: forecast.distribution ?? null,
    probability_semantics: forecast.probability_semantics ?? null,
  };
}

export function displayQuestion(facts: ForecastFacts): DisplayedQuestion {
  const question_key = facts.question_key?.trim() || null;
  const entry = question_key ? classifyQuestionKey(question_key) : null;
  const definition = facts.definition_text?.trim() || entry?.definition || null;
  const question_text = facts.question_text?.trim() || null;
  const horizon = horizonLabel(facts);
  const outcome_id = entry?.outcome_id ?? "unknown";
  const id = [question_key ?? "", outcome_id, definition ?? "", question_text ?? "", horizon].join("\u001f");
  return { id, question_key, question_text, definition, horizon, outcome_id };
}

/** One row per definition, outcome, and horizon. Numeric values are dropped. */
export function distinctQuestions(facts: readonly ForecastFacts[]): DisplayedQuestion[] {
  const seen = new Map<string, DisplayedQuestion>();
  for (const fact of facts) {
    const question = displayQuestion(fact);
    if (!seen.has(question.id)) seen.set(question.id, question);
  }
  return [...seen.values()];
}

function questionCopy(question: DisplayedQuestion, topicDefinition: string): string | null {
  if (question.definition && question.definition !== topicDefinition) return question.definition;
  if (!question.definition && question.question_text && question.question_text !== topicDefinition) return question.question_text;
  if (!question.definition && !question.question_text) return "No definition recorded";
  return null;
}

export function QuestionHorizonList({
  topicDefinition,
  questions,
  headingLevel = "h2",
  headingId = "question-horizons",
  includeTopicDefinition = true,
  notice = true,
  emptyAsUnknown = true,
  partial = null,
}: {
  topicDefinition: string;
  questions: readonly DisplayedQuestion[];
  headingLevel?: "h2" | "h3";
  headingId?: string;
  includeTopicDefinition?: boolean;
  notice?: boolean;
  /** A topic with no statements has an unknown horizon. A filtered empty view does not. */
  emptyAsUnknown?: boolean;
  partial?: { shown: number; total: number } | null;
}) {
  const Heading = headingLevel;
  const rows = questions.length > 0 ? questions : [];
  return (
    <section aria-labelledby={headingId}>
      <Heading id={headingId}>Definitions and horizons</Heading>
      {notice ? <p>{SEPARATE_QUESTIONS}</p> : null}
      {includeTopicDefinition ? <p>{topicDefinition}</p> : null}
      {rows.length > 0 ? (
        <ul>
          {rows.map((question) => {
            const copy = questionCopy(question, includeTopicDefinition ? topicDefinition : "");
            return (
              <li key={question.id}>
                {copy ? <p>{copy}</p> : null}
                {question.question_text && question.definition && question.question_text !== question.definition ? (
                  <p>{question.question_text}</p>
                ) : null}
                <p className="meta">Horizon {question.horizon}</p>
              </li>
            );
          })}
        </ul>
      ) : emptyAsUnknown ? (
        <p className="meta">Horizon unknown</p>
      ) : (
        <p className="meta">This view has no statements.</p>
      )}
      {partial && partial.total > partial.shown ? (
        <p className="meta">These horizons are from the newest {partial.shown} of {partial.total} statements.</p>
      ) : null}
    </section>
  );
}

export function StatementQuestionLine({ statement }: { statement: QuestionSource }) {
  const question = displayQuestion(statementFacts(statement));
  return (
    <p className="meta">
      Definition {question.definition ?? "No definition recorded"}
      {" · "}
      Horizon {question.horizon}
    </p>
  );
}
