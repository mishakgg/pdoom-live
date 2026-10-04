import { ZodError } from "zod";
import {
  PUBLIC_API_LIMITS,
  parseSearchParams,
  publicPageQuerySchema,
  publicPeopleQuerySchema,
  publicSearchQuerySchema,
  publicStatementQuerySchema,
  type PublicPageQuery,
  type PublicPeopleQuery,
  type PublicStatementQuery,
} from "@pdoom/contracts";
import {
  AdmissionError,
  InvalidCursorError,
  SearchTimeoutError,
  isStatementTimeout,
  getDatasetStamp,
  getPool,
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
import type pg from "pg";
import openApiDocument from "@pdoom/contracts/openapi/public-v1.openapi.json";
import { FlightLimitError } from "./single-flight";
import { publicApiLimiter, publicClientKey } from "./rate-limit";
import { apiEnvelope, applyPublicValidators, publicError, publicJson, representPublicJson } from "./public-http";
import { loadPublicRepresentation, representationKey } from "./representation-cache";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

type Route =
  | { kind: "openapi" }
  | { kind: "dataset" }
  | { kind: "people"; query: PublicPeopleQuery }
  | { kind: "person"; slug: string }
  | { kind: "statements"; query: PublicStatementQuery }
  | { kind: "statement"; slug: string }
  | { kind: "topics" }
  | { kind: "topic"; slug: string }
  | { kind: "sources"; query: PublicPageQuery }
  | { kind: "source"; slug: string }
  | { kind: "source-item"; slug: string }
  | { kind: "trends" }
  | { kind: "trend"; slug: string }
  | { kind: "search"; q: string }
  | { kind: "missing" };

function fail(error: unknown): Response {
  if (error instanceof AdmissionError || error instanceof FlightLimitError) {
    const retryAfter = error instanceof AdmissionError ? error.retryAfter : 1;
    return publicError(429, "rate_limited", "Too many requests. Retry later, or generate a bulk snapshot.", {
      "retry-after": String(retryAfter),
    });
  }
  if (error instanceof SearchTimeoutError) {
    return publicError(400, "query_too_expensive", "That search is too expensive. Use a shorter or more specific query.");
  }
  if (isStatementTimeout(error)) {
    return publicError(503, "query_failed", "The query timed out. Retry later.");
  }
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

function resolveRoute(url: URL): Route {
  const segments = url.pathname.replace(/\/+$/, "").split("/").filter(Boolean);
  if (segments[0] !== "api" || segments[1] !== "v1") return { kind: "missing" };
  const rest = segments.slice(2);
  if (rest.length === 1 && rest[0] === "openapi.json") {
    noQuery(url);
    return { kind: "openapi" };
  }
  const route = rest.join("/");
  if (route === "dataset") {
    noQuery(url);
    return { kind: "dataset" };
  }
  if (route === "people") return { kind: "people", query: publicPeopleQuerySchema.parse(parseSearchParams(url.searchParams)) };
  if (rest[0] === "people" && rest.length === 2) {
    noQuery(url);
    return { kind: "person", slug: requireSlug(rest[1]) };
  }
  if (route === "statements") {
    return { kind: "statements", query: publicStatementQuerySchema.parse(parseSearchParams(url.searchParams)) };
  }
  if (rest[0] === "statements" && rest.length === 2) {
    noQuery(url);
    return { kind: "statement", slug: requireSlug(rest[1]) };
  }
  if (route === "topics") {
    noQuery(url);
    return { kind: "topics" };
  }
  if (rest[0] === "topics" && rest.length === 2) {
    noQuery(url);
    return { kind: "topic", slug: requireSlug(rest[1]) };
  }
  if (route === "sources") return { kind: "sources", query: publicPageQuerySchema.parse(parseSearchParams(url.searchParams)) };
  if (rest[0] === "sources" && rest.length === 2) {
    noQuery(url);
    return { kind: "source", slug: requireSlug(rest[1]) };
  }
  if (rest[0] === "source-items" && rest.length === 2) {
    noQuery(url);
    return { kind: "source-item", slug: requireSlug(rest[1]) };
  }
  if (route === "trends") {
    noQuery(url);
    return { kind: "trends" };
  }
  if (rest[0] === "trends" && rest.length === 2) {
    noQuery(url);
    return { kind: "trend", slug: requireSlug(rest[1]) };
  }
  if (route === "search") {
    const query = publicSearchQuerySchema.parse(parseSearchParams(url.searchParams));
    return { kind: "search", q: query.q };
  }
  return { kind: "missing" };
}

async function produce(route: Route, db: pg.PoolClient) {
  const stamp = await getDatasetStamp(db);
  const headers = stampHeaders(stamp);
  const asOf = stamp.imported_at ?? "1970-01-01T00:00:00.000Z";
  if (route.kind === "dataset") {
    return representPublicJson(apiEnvelope(await getPublicCatalog(stamp.imported_at, db)), headers);
  }
  if (route.kind === "people") {
    const page = await listPublicPeople(route.query, db);
    return representPublicJson(apiEnvelope(page.data, page.page), headers);
  }
  if (route.kind === "person") {
    const person = await getPublicPerson(route.slug, db);
    if (!person) return null;
    return representPublicJson(apiEnvelope(person), headers);
  }
  if (route.kind === "statements") {
    const page = await listPublicStatements(route.query, db);
    return representPublicJson(apiEnvelope(page.data, page.page), headers);
  }
  if (route.kind === "statement") {
    const statement = await getPublicStatement(route.slug, db);
    if (!statement) return null;
    return representPublicJson(apiEnvelope(statement), headers);
  }
  if (route.kind === "topics") {
    const topics = await listPublicTopics(db);
    return representPublicJson(apiEnvelope(topics.data, undefined, topics.truncated ? { truncated: true } : {}), headers);
  }
  if (route.kind === "topic") {
    const topic = await getPublicTopic(route.slug, db);
    if (!topic) return null;
    return representPublicJson(apiEnvelope(topic), headers);
  }
  if (route.kind === "sources") {
    const page = await listPublicSources(route.query, asOf, db);
    return representPublicJson(apiEnvelope(page.data, page.page), headers);
  }
  if (route.kind === "source") {
    const source = await getPublicSource(route.slug, asOf, db);
    if (!source) return null;
    return representPublicJson(apiEnvelope(source), headers);
  }
  if (route.kind === "source-item") {
    const item = await getPublicSourceItem(route.slug, db);
    if (!item) return null;
    return representPublicJson(apiEnvelope(item), headers);
  }
  if (route.kind === "trends") {
    const trends = await listPublicTrends(db);
    return representPublicJson(apiEnvelope(trends.data), headers);
  }
  if (route.kind === "trend") {
    const trend = await getPublicTrend(route.slug, asOf, db);
    if (!trend) return null;
    return representPublicJson(apiEnvelope(trend), headers);
  }
  if (route.kind === "search") {
    return representPublicJson(apiEnvelope(await searchResearch(route.q, db)), headers);
  }
  return null;
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
  try {
    const route = resolveRoute(url);
    if (route.kind === "missing") return publicError(404, "not_found", "Not found.");
    if (route.kind === "openapi") return publicJson(request, openApiDocument);
    const representation = await loadPublicRepresentation(representationKey(url), getPool(), (db) => produce(route, db));
    if (!representation) {
      const label =
        route.kind === "person"
          ? "Person"
          : route.kind === "statement"
            ? "Statement"
            : route.kind === "topic"
              ? "Topic"
              : route.kind === "source"
                ? "Source"
                : route.kind === "source-item"
                  ? "Source item"
                  : route.kind === "trend"
                    ? "Trend"
                    : "Record";
      return publicError(404, "not_found", `${label} not found.`);
    }
    return applyPublicValidators(request, representation);
  } catch (error) {
    return fail(error);
  }
}
