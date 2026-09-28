/**
 * Smoke budgets for a production `next start` on loopback after one warmup request.
 * They are loose for GitHub-hosted runner variance and tight enough that a multi-second
 * stall, a duplicated framework bundle, or a search request storm fails the suite.
 */
export const budgets = {
  documentResponseMs: 2_500,
  maxJavaScriptBytes: 1_500_000,
  maxIdenticalScriptRequests: 2,
  maxIdenticalApiRequests: 2,
  maxSearchRequests: 3,
  searchResponseMs: 2_000,
} as const;
