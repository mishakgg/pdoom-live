import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  COLLECTION_STATUSES,
  CONFIDENCE_LEVELS,
  IDENTITY_NAMESPACES,
  mapVocabulary,
  normalizePrefixedId,
  normalizeTimestamp,
  PARTICIPANT_ROLES,
  PERSON_STATUSES,
  RELATIONSHIP_TYPES,
  REVIEW_STATES,
  SOURCE_TYPES,
  STATEMENT_TYPES,
  timestampsMatch,
} from "@pdoom/contracts";

const shared = JSON.parse(readFileSync(new URL("../packages/contracts/shared-vocabulary.json", import.meta.url), "utf8"));

describe("shared vocabulary parity", () => {
  it("locks product enums to the shared file", () => {
    expect([...STATEMENT_TYPES]).toEqual(shared.statement_type);
    expect([...REVIEW_STATES]).toEqual(shared.review_state);
    expect([...PARTICIPANT_ROLES]).toEqual(shared.participant_role);
    expect([...IDENTITY_NAMESPACES]).toEqual(shared.identity_namespace);
    expect([...RELATIONSHIP_TYPES]).toEqual(shared.relationship_type);
    expect([...CONFIDENCE_LEVELS]).toEqual(shared.confidence_level);
    expect([...PERSON_STATUSES]).toEqual(shared.person_status);
    for (const value of shared.source_type_shared) expect(SOURCE_TYPES).toContain(value);
    for (const value of shared.collection_status_shared) expect(COLLECTION_STATUSES).toContain(value);
    expect(SOURCE_TYPES).not.toContain("openalex_works");
    expect(COLLECTION_STATUSES).not.toContain("temporarily_unavailable");
  });
});

describe("canonical normalization", () => {
  it("maps collector detail without collapsing unrelated types", () => {
    expect(mapVocabulary("collection_method", "github_api")).toEqual({ canonical: "api", detail: "github_api" });
    expect(mapVocabulary("source_type", "openalex_works")).toEqual({ canonical: "academic_works", detail: "openalex_works" });
    expect(mapVocabulary("verification_method", "openalex_exact_name_and_institution")).toEqual({
      canonical: "structured_academic_source",
      detail: "openalex_exact_name_and_institution",
    });
    expect(mapVocabulary("organization_type", "research_lab")).toEqual({ canonical: "research_lab", detail: null });
    expect(() => mapVocabulary("source_type", "huggingface")).toThrow(/unmapped/);
  });

  it("normalizes prefixed ids and equivalent UTC timestamps", () => {
    expect(normalizePrefixedId("person:ada-quill", "person")).toBe("ada-quill");
    expect(() => normalizePrefixedId("person:", "person")).toThrow(/malformed/);
    expect(() => normalizePrefixedId("ada-quill", "person")).toThrow(/malformed/);
    expect(timestampsMatch("2026-09-24T01:56:39Z", "2026-09-24T01:56:39+00:00")).toBe(true);
    expect(normalizeTimestamp("2026-09-24T01:56:39Z")).toBe("2026-09-24T01:56:39.000Z");
    expect(() => normalizeTimestamp("2026-09-24 01:56:39")).toThrow(/invalid timestamp/);
  });
});
