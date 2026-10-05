/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { PublicCatalog } from "@pdoom/db";
import { formatWhen } from "@/lib/format";
import { DataDocument, datasetFreshnessCopy, type DatasetFreshnessInput } from "./page";

const VALIDATOR =
  "Responses send ETag and Cache-Control. Last-Modified is not sent. If-Modified-Since does not change the response. A 304 is returned only when If-None-Match matches the current body.";

const GENERATED_AT = "2020-01-02T03:04:00.000Z";
const IMPORTED_AT = "2024-03-01T12:00:00.000Z";

afterEach(() => {
  cleanup();
});

type Coverage = Parameters<typeof DataDocument>[0]["coverage"];

function catalog(input: { dataset: PublicCatalog["dataset"]; cohort: PublicCatalog["cohort"] }): PublicCatalog {
  return {
    api_version: "v1",
    export_schema_version: "1.0.0",
    as_of: null,
    dataset: input.dataset,
    cohort: input.cohort,
    methodology: {
      cohort_methodology_ref: "docs/COHORT_METHODOLOGY.md",
      cohort_methodology_version: "1.0.0",
      cohort_methodology_note: "Written methodology.",
      provenance_policy_ref: "docs/SOURCE_AND_PROVENANCE_POLICY.md",
      public_api_ref: "docs/PUBLIC_API.md",
      trend_method_versions: [],
      topic_versions: [],
    },
    publication: {
      included_review_states: ["human_verified", "machine_validated"],
      excluded_review_states: ["needs_review", "unreviewed", "rejected"],
      machine_validated: "machine",
      site_difference: "The website can show needs_review statements as unsettled.",
    },
    license: { status: "pending", note: "License note." },
    counts: {
      people: 40,
      organizations: 1,
      identities: 1,
      sources: 1,
      source_items: 1,
      statements: 3,
      forecasts: 1,
      topics: 1,
      relationships: 0,
      trends: 0,
    },
    latest_observed_at: null,
    latest_published_at: null,
    latest_source_checked_at: null,
    latest_source_success_at: null,
  };
}

function coverage(overrides: Partial<Coverage> = {}): Coverage {
  return {
    as_of: "1999-01-01T00:00:00.000Z",
    cohort_slug: null,
    cohort_version: null,
    cohort_size: 99,
    people_with_sources: 0,
    people_with_non_academic_sources: 0,
    people_with_first_party_sources: 0,
    statement_bearing_people: 0,
    public_statement_count: 0,
    recent_successfully_checked_sources: 0,
    sources_by_type: {},
    source_count: 0,
    latest_successful_observation: null,
    latest_source_checked_at: null,
    latest_item_observed_at: null,
    stale_sources: 0,
    unavailable_or_failing_sources: 0,
    freshness: { current: 0, aging: 0, stale: 0, never_checked: 0 },
    ...overrides,
  };
}

function dataset(importedAt: string | null): NonNullable<PublicCatalog["dataset"]> {
  return {
    dataset_id: "synthetic-frontier-v1",
    dataset_kind: "synthetic",
    import_schema_version: "1.0.0",
    source_generated_at: GENERATED_AT,
    imported_at: importedAt,
    notice: "A labeled synthetic fixture.",
    producer_name: null,
    producer_version: null,
  };
}

function cohort(): NonNullable<PublicCatalog["cohort"]> {
  return {
    slug: "cohort_2026_09",
    version: "2026.09.0",
    name: "Frontier seed",
    definition: "A purposive seed.",
  };
}

function renderDocument(input: { dataset: PublicCatalog["dataset"]; cohort: PublicCatalog["cohort"]; coverage?: Partial<Coverage> }) {
  render(
    <DataDocument
      catalog={catalog({ dataset: input.dataset, cohort: input.cohort })}
      coverage={coverage(input.coverage)}
    />,
  );
}

function freshnessStatement(): HTMLElement {
  const section = screen.getByRole("heading", { name: "Freshness" }).closest("section");
  const paragraph = section?.querySelector("p");
  if (!paragraph) throw new Error("missing freshness statement");
  return paragraph;
}

function field(term: string): string {
  const termNode = screen.getByText(term, { selector: "dt" });
  return termNode.parentElement?.querySelector("dd")?.textContent ?? "";
}

function expectValidatorCopy() {
  const section = screen.getByRole("heading", { name: "API" }).closest("section");
  const paragraph = Array.from(section?.querySelectorAll("p") ?? []).find((node) => node.textContent?.includes("Responses send"));
  expect(paragraph?.textContent).toContain(VALIDATOR);
  expect(Array.from(paragraph?.querySelectorAll("code") ?? [], (node) => node.textContent)).toEqual([
    "ETag",
    "Cache-Control",
    "Last-Modified",
    "If-Modified-Since",
    "If-None-Match",
  ]);
  expect(document.body.textContent).not.toContain("from the dataset import time");
}

describe("public data page freshness", () => {
  it("names the stored dataset and cohort and leaves a missing import time unknown", () => {
    renderDocument({
      dataset: dataset(null),
      cohort: cohort(),
      coverage: { cohort_slug: "cohort_2026_09", cohort_version: "2026.09.0", cohort_size: 12 },
    });

    const statement = freshnessStatement();
    expect(statement.textContent).toBe(
      "Loaded dataset synthetic-frontier-v1, version 1.0.0, cohort cohort_2026_09 2026.09.0. Import time unknown. Cohort membership is 12. The count is the loaded cohort, not all AI researchers.",
    );
    expect(statement.textContent).not.toContain(formatWhen(GENERATED_AT));
    expect(statement.textContent).not.toContain(GENERATED_AT);
    expect(statement.textContent).not.toMatch(/\d{4}-\d{2}-\d{2}T/);
    expect(field("Dataset updated")).toBe("Time unknown");
    expect(field("Dataset generated")).toBe(formatWhen(GENERATED_AT));
    expect(document.querySelector("p.fresh")?.textContent).toContain("Synthetic fixture");
    expect(document.querySelector("p.fresh")?.textContent).toContain("synthetic-frontier-v1");
    expect(document.querySelector("p.fresh")?.textContent).toContain("Frontier seed");
    expect(document.querySelector("p.fresh")?.textContent).toContain("2026.09.0");
    expectValidatorCopy();
  });

  it("shows the stored import time and does not replace it", () => {
    renderDocument({
      dataset: dataset(IMPORTED_AT),
      cohort: cohort(),
      coverage: { cohort_size: 12 },
    });

    const statement = freshnessStatement();
    expect(statement.textContent).toBe(
      `Loaded dataset synthetic-frontier-v1, version 1.0.0, cohort cohort_2026_09 2026.09.0. Imported ${formatWhen(IMPORTED_AT)}. Cohort membership is 12. The count is the loaded cohort, not all AI researchers.`,
    );
    expect(statement.textContent).not.toContain("Import time unknown");
    expect(field("Dataset updated")).toBe(formatWhen(IMPORTED_AT));
    expect(field("Dataset updated")).not.toBe(formatWhen(GENERATED_AT));
    expect(screen.getByRole("heading", { name: "License and citation" }).closest("section")?.textContent).toContain(IMPORTED_AT);
    expectValidatorCopy();
  });

  it("does not invent a cohort count or an import time when neither is stored", () => {
    renderDocument({ dataset: null, cohort: null });

    const statement = freshnessStatement();
    expect(statement.textContent).toBe(
      "No dataset is loaded. Import time unknown. The count is the loaded cohort, not all AI researchers.",
    );
    expect(statement.textContent).not.toContain("99");
    expect(statement.textContent).not.toContain("UTC");
    expect(field("Dataset updated")).toBe("Time unknown");
    expect(document.querySelector("p.fresh")?.textContent).toContain("No dataset loaded");
    expect(document.querySelector("p.fresh")?.textContent).not.toContain("Live dataset");
    expectValidatorCopy();
  });

  it("uses a cohort stored on the coverage read when the catalog cohort row is absent", () => {
    renderDocument({
      dataset: dataset(null),
      cohort: null,
      coverage: { cohort_slug: "cohort_2026_10", cohort_version: "2026.10.0", cohort_size: 7 },
    });

    expect(freshnessStatement().textContent).toBe(
      "Loaded dataset synthetic-frontier-v1, version 1.0.0, cohort cohort_2026_10 2026.10.0. Import time unknown. Cohort membership is 7. The count is the loaded cohort, not all AI researchers.",
    );
  });

  it("labels an unreadable import time unknown", () => {
    const input: DatasetFreshnessInput = {
      datasetId: "synthetic-frontier-v1",
      datasetVersion: "1.0.0",
      cohortSlug: "cohort_2026_09",
      cohortVersion: "2026.09.0",
      cohortSize: 12,
      importedAt: "not-a-timestamp",
    };
    expect(datasetFreshnessCopy(input)).toBe(
      "Loaded dataset synthetic-frontier-v1, version 1.0.0, cohort cohort_2026_09 2026.09.0. Import time unknown. Cohort membership is 12. The count is the loaded cohort, not all AI researchers.",
    );
    expect(datasetFreshnessCopy(input)).not.toContain("not-a-timestamp");
  });
});
