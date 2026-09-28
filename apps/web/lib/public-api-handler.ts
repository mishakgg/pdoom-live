import { ZodError } from "zod";
import {
  PUBLIC_API_LIMITS,
  parseSearchParams,
  publicPageQuerySchema,
  publicPeopleQuerySchema,
  publicSearchQuerySchema,
  publicStatementQuerySchema,
} from "@pdoom/contracts";
import {
  InvalidCursorError,
  getDatasetStamp,
  getPublicCatalog,
  getPublicPerson,
  getPublicSource,
  getPublicSourceItem,
  getPublicStatement,
  getPublicTopic,
  getPublicTrend,
  listPublicPeople,
  listPublicSources,
  listPublicStatements,
  listPublicTopics,
  listPublicTrends,
  searchResearch,
} from "@pdoom/db";
import openApiDocument from "@pdoom/contracts/openapi/public-v1.openapi.json";
import { publicApiLimiter, publicClientKey } from "./rate-limit";
import { apiEnvelope, publicError, publicJson } from "./public-http";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function fail(error: unknown): Response {
  if (error instanceof InvalidCursorError) return publicError(400, "invalid_cursor", "Cursor is invalid.");
  if (error instanceof ZodError) return publicError(400, "invalid_query", "Query parameters are invalid.");
  if (error instanceof Error && error.message.startsWith("duplicate query")) {
    return publicError(400, "invalid_query", "Duplicate query parameters are not accepted.");
  }
  if (error instanceof Error && error.message === "unexpected_query") {
    return publicError(400, "invalid_query", "This route does not accept query parameters.");
  }
  if (error instanceof Error && error.message === "invalid_slug") {
    return publicError(400, "invalid_query", "Slug is invalid.");
  }
  console.error("public query failed");
  return publicError(500, "query_failed", "The query could not be completed.");
}

function requireSlug(value: string | undefined): string {
  if (!value || value.length > 80 || !SLUG.test(value)) throw new Error("invalid_slug");
  return value;
}

function noQuery(url: URL) {
  if ([...url.searchParams.keys()].length > 0) {
    throw new Error("unexpected_query");
  }
}

function stampHeaders(stamp: { dataset_id: string | null; dataset_kind: string | null }) {
  const headers: Record<string, string> = {};
  if (stamp.dataset_id) headers["x-dataset-id"] = stamp.dataset_id;
  if (stamp.dataset_kind) headers["x-dataset-kind"] = stamp.dataset_kind;
  return headers;
}

export async function handlePublicApi(request: Request): Promise<Response> {
  if (request.method !== "GET") return publicError(405, "method_not_allowed", "The public API is read-only.");
  const decision = publicApiLimiter.consume(publicClientKey(request));
  if (!decision.ok) {
    return publicError(429, "rate_limited", "Too many requests. Retry later, or generate a bulk snapshot.", {
      "retry-after": String(decision.retryAfter),
    });
  }
  const url = new URL(request.url);
  if (url.search.length > PUBLIC_API_LIMITS.maxQueryStringLength) {
    return publicError(400, "invalid_query", "Query string exceeds the length limit.");
  }
  const segments = url.pathname.replace(/\/+$/, "").split("/").filter(Boolean);
  if (segments[0] !== "api" || segments[1] !== "v1") return publicError(404, "not_found", "Not found.");
  const rest = segments.slice(2);
  if (rest.length === 1 && rest[0] === "openapi.json") {
    try {
      noQuery(url);
    } catch (error) {
      return fail(error);
    }
    return publicJson(request, openApiDocument, null);
  }
  try {
    const stamp = await getDatasetStamp();
    const headers = stampHeaders(stamp);
    const asOf = stamp.imported_at ?? "1970-01-01T00:00:00.000Z";
    const route = rest.join("/");

    if (route === "dataset") {
      noQuery(url);
      return publicJson(request, apiEnvelope(await getPublicCatalog(stamp.imported_at)), stamp.imported_at, headers);
    }
    if (route === "people") {
      const page = await listPublicPeople(publicPeopleQuerySchema.parse(parseSearchParams(url.searchParams)));
      return publicJson(request, apiEnvelope(page.data, page.page), stamp.imported_at, headers);
    }
    if (rest[0] === "people" && rest.length === 2) {
      noQuery(url);
      const person = await getPublicPerson(requireSlug(rest[1]));
      if (!person) return publicError(404, "not_found", "Person not found.");
      return publicJson(request, apiEnvelope(person), stamp.imported_at, headers);
    }
    if (route === "statements") {
      const page = await listPublicStatements(publicStatementQuerySchema.parse(parseSearchParams(url.searchParams)));
      return publicJson(request, apiEnvelope(page.data, page.page), stamp.imported_at, headers);
    }
    if (rest[0] === "statements" && rest.length === 2) {
      noQuery(url);
      const statement = await getPublicStatement(requireSlug(rest[1]));
      if (!statement) return publicError(404, "not_found", "Statement not found.");
      return publicJson(request, apiEnvelope(statement), stamp.imported_at, headers);
    }
    if (route === "topics") {
      noQuery(url);
      const topics = await listPublicTopics();
      return publicJson(
        request,
        apiEnvelope(topics.data, undefined, topics.truncated ? { truncated: true } : {}),
        stamp.imported_at,
        headers,
      );
    }
    if (rest[0] === "topics" && rest.length === 2) {
      noQuery(url);
      const topic = await getPublicTopic(requireSlug(rest[1]));
      if (!topic) return publicError(404, "not_found", "Topic not found.");
      return publicJson(request, apiEnvelope(topic), stamp.imported_at, headers);
    }
    if (route === "sources") {
      const page = await listPublicSources(publicPageQuerySchema.parse(parseSearchParams(url.searchParams)), asOf);
      return publicJson(request, apiEnvelope(page.data, page.page), stamp.imported_at, headers);
    }
    if (rest[0] === "sources" && rest.length === 2) {
      noQuery(url);
      const source = await getPublicSource(requireSlug(rest[1]), asOf);
      if (!source) return publicError(404, "not_found", "Source not found.");
      return publicJson(request, apiEnvelope(source), stamp.imported_at, headers);
    }
    if (rest[0] === "source-items" && rest.length === 2) {
      noQuery(url);
      const item = await getPublicSourceItem(requireSlug(rest[1]));
      if (!item) return publicError(404, "not_found", "Source item not found.");
      return publicJson(request, apiEnvelope(item), stamp.imported_at, headers);
    }
    if (route === "trends") {
      noQuery(url);
      const trends = await listPublicTrends();
      return publicJson(request, apiEnvelope(trends.data), stamp.imported_at, headers);
    }
    if (rest[0] === "trends" && rest.length === 2) {
      noQuery(url);
      const trend = await getPublicTrend(requireSlug(rest[1]), asOf);
      if (!trend) return publicError(404, "not_found", "Trend not found.");
      return publicJson(request, apiEnvelope(trend), stamp.imported_at, headers);
    }
    if (route === "search") {
      const query = publicSearchQuerySchema.parse(parseSearchParams(url.searchParams));
      return publicJson(request, apiEnvelope(await searchResearch(query.q)), stamp.imported_at, headers);
    }
    return publicError(404, "not_found", "Not found.");
  } catch (error) {
    return fail(error);
  }
}
