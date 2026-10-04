/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { HistoryPreview } from "../apps/web/components/history-preview";
import { PersonProfile, type PersonProfileData } from "../apps/web/components/person-profile";

afterEach(() => {
  cleanup();
});

function person(overrides: Partial<PersonProfileData> = {}): PersonProfileData {
  return {
    slug: "ada-quill",
    display_name: "Ada Quill",
    bio_short: "Research lead.",
    status: "active",
    inclusion_reason: "Included for the fixture.",
    cohort_tags: [],
    updated_at: null,
    affiliations: [],
    identities: [],
    sources: [],
    statements: [
      {
        slug: "newest",
        statement_type: "explicit_numeric",
        normalized_text: "A sourced estimate.",
        event_time: "2024-01-01T00:00:00.000Z",
        review_state: "human_verified",
        person: { slug: "ada-quill", display_name: "Ada Quill" },
        source: { slug: "notes", name: "Notes", source_type: "blog" },
        source_item: { published_at: "2020-01-01T00:00:00.000Z", observed_at: "2024-02-01T00:00:00.000Z" },
        forecast: null,
        topics: [{ slug: "ai-extinction", name: "Human extinction from AI" }],
      },
    ],
    statement_total: 60,
    ...overrides,
  };
}

describe("longitudinal profile", () => {
  it("says a 50-statement cap is a preview and keeps the person and topic on the paged list", () => {
    render(
      <PersonProfile
        person={person()}
        navigation={{
          filters: { person: "ada-quill", topic: "ai-extinction", from: "2020-01-01", review_state: "human_verified" },
          narrowed: true,
          unfilteredTotal: 80,
        }}
      />,
    );
    expect(screen.getByText(/1 of 60/)).toBeTruthy();
    expect(screen.getByText(/not the complete history/)).toBeTruthy();
    expect(screen.getByText(/80 public statements are collected/)).toBeTruthy();
    const list = screen.getByRole("link", { name: "Open the paged statement list" });
    expect(list.getAttribute("href")).toBe(
      "/statements?person=ada-quill&topic=ai-extinction&review_state=human_verified&from=2020-01-01",
    );
    const topicLinks = screen.getAllByRole("link", { name: /Human extinction from AI/ });
    expect(topicLinks.length).toBeGreaterThan(0);
    for (const link of topicLinks) {
      expect(link.getAttribute("href")).toBe(
        "/topics/ai-extinction?person=ada-quill&review_state=human_verified&from=2020-01-01",
      );
    }
    expect(screen.getByText(/Collected after publication/)).toBeTruthy();
    expect(screen.getByRole("link", { name: /All explicit numerical estimate records/ })).toBeTruthy();
    expect(screen.getByText(/does not turn those links into an overall belief/)).toBeTruthy();
  });

  it("does not describe a filtered-out history as never collected", () => {
    render(
      <PersonProfile
        person={person({ statements: [], statement_total: 0 })}
        navigation={{
          filters: { person: "ada-quill", statement_type: "explicit_qualitative" },
          narrowed: true,
          unfilteredTotal: 4,
        }}
      />,
    );
    expect(screen.getByText(/No statement in this view matches the selected filters/)).toBeTruthy();
    expect(screen.getByText(/4 public statements are collected for this person before these filters/)).toBeTruthy();
    expect(screen.queryByText("No statement has been collected for this record.")).toBeNull();
    expect(screen.getByRole("link", { name: "Open the paged statement list" }).getAttribute("href")).toBe(
      "/statements?person=ada-quill&statement_type=explicit_qualitative",
    );
  });

  it("offers the paged list even when the current view is complete", () => {
    render(<HistoryPreview shown={4} total={4} href="/statements?person=ada-quill" />);
    expect(screen.getByText(/All 4 public statements/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open the paged statement list" }).getAttribute("href")).toBe(
      "/statements?person=ada-quill",
    );
  });
});
