import type { ReviewState } from "./enums";

export type ReviewPresentation = {
  /** Visible on a public page. Rejected records stay hidden. */
  public: boolean;
  verified: boolean;
  machine_labeled: boolean;
  /** Eligible for sitemaps, feeds, and search-engine indexing. */
  indexable: boolean;
};

const POLICY: Record<ReviewState, ReviewPresentation> = {
  rejected: { public: false, verified: false, machine_labeled: false, indexable: false },
  needs_review: { public: true, verified: false, machine_labeled: false, indexable: false },
  unreviewed: { public: false, verified: false, machine_labeled: false, indexable: false },
  machine_validated: { public: true, verified: false, machine_labeled: true, indexable: true },
  human_verified: { public: true, verified: true, machine_labeled: false, indexable: true },
};

export function reviewPresentation(state: ReviewState): ReviewPresentation {
  return POLICY[state];
}

export function isPublicReviewState(state: string): boolean {
  return state in POLICY && POLICY[state as ReviewState].public;
}

export function isVerifiedReviewState(state: string): boolean {
  return state in POLICY && POLICY[state as ReviewState].verified;
}

/** States that may be advertised to crawlers and syndication clients. */
export function isIndexableReviewState(state: string): boolean {
  return state in POLICY && POLICY[state as ReviewState].indexable;
}

/** Person rows in the public index. `review` stays on site pages and out of discovery. */
export const INDEXABLE_PERSON_STATUSES = ["active", "historical"] as const;

export function isIndexablePersonStatus(status: string): boolean {
  return (INDEXABLE_PERSON_STATUSES as readonly string[]).includes(status);
}
