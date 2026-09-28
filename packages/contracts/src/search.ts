import { z } from "zod";
import { REVIEW_STATES, STATEMENT_TYPES } from "./enums";
import { isPublicReviewState } from "./review";

const slug = z
  .string()
  .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)
  .max(80);

const queryDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

/** Public discovery kinds. Unpublished source bodies are not a kind. */
export const SEARCH_ENTITY_TYPES = [
  "person",
  "organization",
  "statement",
  "topic",
  "source",
  "source_item",
] as const;
export type SearchEntityType = (typeof SEARCH_ENTITY_TYPES)[number];

/**
 * Winning match tier. Higher tiers sort first. The integer is a sort key,
 * not a model score and not a judgment of the person.
 */
export const SEARCH_MATCHES = [
  "exact_text",
  "exact_name",
  "family_name",
  "name_prefix",
  "token_prefix",
  "phrase",
  "all_tokens",
  "affiliation_role",
] as const;
export type SearchMatch = (typeof SEARCH_MATCHES)[number];

export const SEARCH_RANK: Record<SearchMatch, number> = {
  exact_text: 460,
  exact_name: 400,
  family_name: 320,
  name_prefix: 240,
  token_prefix: 180,
  phrase: 380,
  all_tokens: 100,
  affiliation_role: 60,
};

export const SEARCH_QUERY_MAX = 200;
export const SEARCH_TOKEN_LIMIT = 8;
export const SEARCH_TOKEN_LENGTH = 48;
export const SEARCH_DEBOUNCE_MS = 200;
export const SEARCH_SUGGEST_MIN = 2;
export const SEARCH_PAGE_LIMIT_DEFAULT = 8;
export const SEARCH_PAGE_LIMIT_MAX = 20;

/** Per-type caps for the navigation suggester. The sum is the suggest bound. */
export const SEARCH_SUGGEST_LIMITS: Record<SearchEntityType, number> = {
  person: 2,
  organization: 1,
  statement: 2,
  topic: 1,
  source: 1,
  source_item: 1,
};

const INVISIBLE = /[\u00AD\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFEFF]/g;
const CONTROLS = /[\u0000-\u001F\u007F]/g;

export function normalizeSearchText(input: string): string {
  return input.normalize("NFKC").replace(INVISIBLE, "").replace(CONTROLS, " ").replace(/\s+/gu, " ").trim();
}

export function escapeLike(input: string): string {
  return input.replace(/[!%_\\]/g, (char) => `!${char}`);
}

export function prepareSearchText(input: string): {
  normalized: string;
  likeNorm: string;
  tokens: string[];
  truncated: boolean;
  reason: "ok" | "empty" | "no_tokens";
} {
  const normalized = normalizeSearchText(input).toLowerCase().slice(0, SEARCH_QUERY_MAX);
  if (!normalized) {
    return { normalized: "", likeNorm: "", tokens: [], truncated: false, reason: "empty" };
  }
  const parts = normalized.split(/[^\p{L}\p{N}]+/u).filter((part) => part.length >= 2);
  const truncated = parts.length > SEARCH_TOKEN_LIMIT || parts.some((part) => part.length > SEARCH_TOKEN_LENGTH);
  const tokens: string[] = [];
  const seen = new Set<string>();
  for (const part of parts) {
    const token = part.slice(0, SEARCH_TOKEN_LENGTH);
    if (token.length < 2 || seen.has(token)) continue;
    seen.add(token);
    tokens.push(token);
    if (tokens.length >= SEARCH_TOKEN_LIMIT) break;
  }
  return {
    normalized,
    likeNorm: escapeLike(normalized),
    tokens,
    truncated,
    reason: tokens.length ? "ok" : "no_tokens",
  };
}

const dateScoped = new Set<SearchEntityType>(["statement", "source_item"]);
const topicScoped = new Set<SearchEntityType>(["statement", "topic"]);
const personScoped = new Set<SearchEntityType>(["person", "statement", "source", "source_item"]);

export function searchTypesForFilters(input: {
  type?: SearchEntityType | undefined;
  statement_type?: string | undefined;
  from?: string | undefined;
  to?: string | undefined;
  topic?: string | undefined;
  person?: string | undefined;
}): SearchEntityType[] {
  let kinds = new Set<SearchEntityType>(input.type ? [input.type] : SEARCH_ENTITY_TYPES);
  if (input.statement_type) kinds = new Set([...kinds].filter((kind) => kind === "statement"));
  if (input.from || input.to) kinds = new Set([...kinds].filter((kind) => dateScoped.has(kind)));
  if (input.topic) kinds = new Set([...kinds].filter((kind) => topicScoped.has(kind)));
  if (input.person) kinds = new Set([...kinds].filter((kind) => personScoped.has(kind)));
  return SEARCH_ENTITY_TYPES.filter((kind) => kinds.has(kind));
}

export const searchQuerySchema = z
  .object({
    q: z.string().trim().min(1).max(SEARCH_QUERY_MAX),
    mode: z.enum(["page", "suggest"]).default("page"),
    type: z.enum(SEARCH_ENTITY_TYPES).optional(),
    topic: slug.optional(),
    person: slug.optional(),
    statement_type: z.enum(STATEMENT_TYPES).optional(),
    from: queryDate.optional(),
    to: queryDate.optional(),
    cursor: z.string().min(1).max(800).optional(),
    limit: z.coerce.number().int().min(1).max(SEARCH_PAGE_LIMIT_MAX).optional(),
  })
  .strict()
  .superRefine((value, ctx) => {
    if (value.from && value.to && value.from > value.to) {
      ctx.addIssue({ code: "custom", message: "from must be on or before to", path: ["from"] });
    }
    if (value.cursor && value.mode === "suggest") {
      ctx.addIssue({ code: "custom", message: "suggest does not paginate", path: ["cursor"] });
    }
    if (value.cursor && !value.type) {
      ctx.addIssue({ code: "custom", message: "cursor requires an entity type", path: ["cursor"] });
    }
    if (value.statement_type && value.type && value.type !== "statement") {
      ctx.addIssue({
        code: "custom",
        message: "statement class applies only to statements",
        path: ["statement_type"],
      });
    }
    if ((value.from || value.to) && value.type && !dateScoped.has(value.type)) {
      ctx.addIssue({ code: "custom", message: "date range applies to statements and source items", path: ["from"] });
    }
    if (value.topic && value.type && !topicScoped.has(value.type)) {
      ctx.addIssue({ code: "custom", message: "topic filter applies to statements and topics", path: ["topic"] });
    }
    if (value.person && value.type && !personScoped.has(value.type)) {
      ctx.addIssue({ code: "custom", message: "person filter does not apply to that entity type", path: ["person"] });
    }
    if (searchTypesForFilters(value).length === 0) {
      ctx.addIssue({ code: "custom", message: "those filters exclude every entity type", path: ["type"] });
    }
  });

export type SearchQuery = z.infer<typeof searchQuerySchema>;

export type SearchHitBase = {
  id: string;
  slug: string;
  match: SearchMatch;
};

export type SearchPersonHit = SearchHitBase & {
  kind: "person";
  display_name: string;
  status: string;
  organization: { slug: string; name: string; role: string | null } | null;
};

export type SearchOrganizationHit = SearchHitBase & {
  kind: "organization";
  name: string;
  organization_type: string;
  affiliation: { person_slug: string; display_name: string; role: string | null } | null;
};

export type SearchStatementHit = SearchHitBase & {
  kind: "statement";
  statement_type: string;
  normalized_text: string;
  event_time: string | null;
  review_state: string;
  person: { slug: string; display_name: string };
  source: { slug: string; name: string; source_type: string };
  source_item: { slug: string; title: string | null; published_at: string | null };
  topics: Array<{ slug: string; name: string }>;
  forecast: {
    horizon_text: string | null;
    value_type: string;
    value_numeric: number | null;
    value_min: number | null;
    value_max: number | null;
    unit: string | null;
  } | null;
};

export type SearchTopicHit = SearchHitBase & {
  kind: "topic";
  name: string;
  definition: string;
};

export type SearchSourceHit = SearchHitBase & {
  kind: "source";
  name: string;
  source_type: string;
  review_state: string;
  owner: { slug: string; display_name: string } | null;
};

export type SearchSourceItemHit = SearchHitBase & {
  kind: "source_item";
  title: string | null;
  published_at: string | null;
  source: { slug: string; name: string; source_type: string };
};

export type SearchHit =
  | SearchPersonHit
  | SearchOrganizationHit
  | SearchStatementHit
  | SearchTopicHit
  | SearchSourceHit
  | SearchSourceItemHit;

export type SearchGroup<T> = {
  data: T[];
  page: { limit: number; total: number; next_cursor: string | null };
};

export type SearchGroups = {
  person: SearchGroup<SearchPersonHit>;
  organization: SearchGroup<SearchOrganizationHit>;
  statement: SearchGroup<SearchStatementHit>;
  topic: SearchGroup<SearchTopicHit>;
  source: SearchGroup<SearchSourceHit>;
  source_item: SearchGroup<SearchSourceItemHit>;
};

export type SearchResponse = {
  query: {
    text: string;
    normalized: string;
    tokens: string[];
    truncated: boolean;
    reason: "ok" | "empty" | "no_tokens";
    types: SearchEntityType[];
  };
  groups: SearchGroups;
};

/** Review states ordinary statement pages already treat as public. */
export function publicReviewStates(): string[] {
  return REVIEW_STATES.filter((state) => isPublicReviewState(state));
}
