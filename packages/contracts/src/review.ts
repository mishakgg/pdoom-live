import type { ReviewState } from "./enums";

export type ReviewPresentation = {
  public: boolean;
  verified: boolean;
  machine_labeled: boolean;
};

const POLICY: Record<ReviewState, ReviewPresentation> = {
  rejected: { public: false, verified: false, machine_labeled: false },
  needs_review: { public: true, verified: false, machine_labeled: false },
  unreviewed: { public: true, verified: false, machine_labeled: false },
  machine_validated: { public: true, verified: false, machine_labeled: true },
  human_verified: { public: true, verified: true, machine_labeled: false },
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
